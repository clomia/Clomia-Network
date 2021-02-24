import socket, random, os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from threading import Thread, Lock
from queue import Queue
from itertools import cycle
from korean_name_generator import namer
from env import SERVER_PRIVATE_IP, PORT_NUMBER, BUF_SIZE, SECRET_CODE

# ? 데이터는 모두 bytes로 다룬다. 로그 찍을때만 인코딩한다
# ? 단, 생성의 경우 str으로 유지한다. 최종 단계에서 한번에 인코딩한다
# ? 닫힌소켓은 죽이자. 클라이언트가 없는데 있을 필요가 없어
#! encode, socket에 인자 넣어


class ResponseSocket(Thread):
    """ 발신용 소켓을 관리한다 """

    def __init__(self, sock_data):
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.lock = Lock()
        # 타겟 클라이언트 전용 데이터 큐
        self.transmit_queue = Queue(20)

    # ? thread.메서드 로 메인 쓰레드에서 사용
    def send(self, data):
        self.transmit_queue.put(data)

    def run(self):
        try:
            while True:
                # * Blocking
                if signal := self.sock.recv(BUF_SIZE):  # 처음꺼는연결 구축신호(SECRET_CODE)
                    with self.lock:
                        # * Blocking
                        data: bytes = self.transmit_queue.get()
                        self.sock.sendall(data)
                else:
                    raise ConnectionResetError from Exception("클라이언트로부터의 응답이 없습니다")
        except ConnectionResetError as e:
            # 클라이언트의 수신용 소켓이 사라짐
            self.sock.close()
            del self.sock
            print(f"소켓을 제거하였습니다.\n{e}")


class InputSocket(Thread):
    """ 수신용 소켓을 관리한다 """

    def __init__(self, sock_data, data_queue: Queue, unique_prefix):
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.unique_prefix: str = unique_prefix
        self.data_queue = data_queue
        self.lock = Lock()

    def run(self):
        try:
            while True:
                # * Blocking
                if data := self.sock.recv(BUF_SIZE):
                    data = self.unique_prefix.encode("utf-8") + data
                    with self.lock:
                        self.data_queue.put(data)
                        self.sock.sendall(SECRET_CODE)
                else:
                    raise ConnectionResetError from Exception("클라이언트로부터 받은 데이터가 없습니다")
        except ConnectionResetError as e:
            # 클라이언트의 발신용 소켓이 사라짐
            self.sock.close()
            del self.sock
            print(f"소켓을 제거하였습니다.\n{e}")


class Connection(Thread):
    """
    클라이언트와의 접속을 관리한다 ResponseSocket과 InputSocket 상위 노드이다
    수신용 소켓과 발신용 소켓을 묶어서 통신경로를 생성한다
    클라이언트의 이름을 지어준다
    """

    _counter = 0

    def __init__(self, input_socket, response_socket, data_queue: Queue):
        super().__init__()
        self.gender_cycle = cycle((False, True))
        self.client_name = namer.generate(next(self.gender_cycle))
        self.input_socket = input_socket
        self.output_thread = ResponseSocket(response_socket)
        self.data_queue = data_queue
        self.lock = Lock()
        Connection._counter += 1
        self.pk = Connection._counter

    def pk_init(self):  # 메타클레스의 속성부여는 init이전에 실행되는게 아니다
        self.unique_prefix = f"ID{self.pk}|{self.client_name}: "
        self.input_thread = InputSocket(self.input_socket, self.data_queue, self.unique_prefix)

    def run(self):
        self.pk_init()
        self.input_thread.start()
        self.output_thread.start()
        self.input_thread.join()
        self.output_thread.join()
        # * Blocking
        # todo 여기서 사라진 유저를 기록
        notice = f"\n안내 메시지: {self.client_name} 님이 없어졌습니다.\n"
        with self.lock:
            self.data_quene.put(notice.encode("utf-8"))

    def send(self, output_data):
        # * output_thread-> Blocking. send 대기중
        self.output_thread.send(output_data)


class Server:
    """ 수많은 접속을 관리한다 Connection의 상위 노드이다 """

    def __init__(self):
        # todo Queue를 상속받아서 로깅 메서드 정의
        self.data_queue = Queue(100)
        # ? 이 큐를 InputSocket인자로 넣는게 아니라 각 소켓에 따로 큐를 할당해준다
        # ? 이 객체에서 data_queue.get을 하고 그 데이터를 각 소켓 큐에 집어넣는다
        # task_done,join으로 해당 큐의 작업들이
        self.inspect_code_generator = lambda: str(random.randint(100, 1000)).encode("utf-8")
        self.connection_threads = []

    def send_everyone(self):
        """ 데이터 큐에 데이터가 들어오면 그것을 모든 클라이언트에게 전송한다 """
        while True:
            data = self.data_queue.get()  # * Blocking
            print(f"데이터 입력을 확인하였습니다. 전송합니다 \n Data: {data.decode()}")
            for thread in self.connection_threads:
                thread.send(data)

    def open(self):
        send_thread = Thread(target=self.send_everyone)
        receive_thread = Thread(target=self.execute_connction)
        send_thread.start()
        receive_thread.start()

    def execute_connction(self):
        """ 커넥션 쓰레드를 생성하고 실행한다 """
        while True:
            input_socket_data, response_socket_data = self.make_connection_thread()  # * Blocking
            thread = Connection(input_socket_data, response_socket_data, self.data_queue)
            self.connection_threads.append(thread)
            print("성공!\n 연결망이 구축되었습니다.")
            thread.start()

    def make_connection_thread(self) -> Thread:
        """
        1. (클라이언트-발신용 소켓) SECRET_CODE로 연결요청
        2.[1] 연결 요청으로 생성->(서버-수신용 소켓) inspect_code 발송
        3. (클라이언트-발신용 소켓) SECRET_CODE로 응답 , (클라이언트 수신용 소켓) inspect_code로 연결 요청
        4.[2] 연결 요청으로 생성->(서버-발신용 소켓) 검사 후 (서버-수신용 소켓)과 묶어서 커넥션 생성
        """
        input_socket_data = self.input_socket_generator()  # * Blocking
        print("InputSocket생성에 성공하였습니다. ResponseSocket을 생성합니다...")
        response_socket_data = self.response_socket_generator()  # * Blocking
        print("ResponseSocket생성에 성공하였습니다. Connection을 생성합니다...")
        return input_socket_data, response_socket_data

    def response_socket_generator(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((SERVER_PRIVATE_IP, PORT_NUMBER))
            server_socket.listen(20)
            client_request = server_socket.accept()  # * Blocking
            try:
                response_socket_data = self.socket_inspect_processing(client_request)
            except ConnectionResetError as e:
                server_socket.close()
                del server_socket
                print(f"[INFO]{client_request[1]}로 소켓 생성에 실패한것을 올바르게 처리하였습니다.")
            else:
                return response_socket_data

    def input_socket_generator(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((SERVER_PRIVATE_IP, PORT_NUMBER))
            server_socket.listen(20)
            client_request = server_socket.accept()  # * Blocking
            try:
                input_socket_data = self.connection_requests_processing(client_request)
            except ConnectionResetError as e:
                server_socket.close()
                del server_socket
                print(f"[INFO]{client_request[1]}로 소켓 생성에 실패한것을 올바르게 처리하였습니다.")
            else:
                return input_socket_data

    def connection_requests_processing(self, client_request) -> socket.socket:
        """
        소켓으로 받은 SECRET_CODE를 확인합니다.
        올바른 요청인 경우 소켓으로 inspect_code를 보내고 소켓을 반환합니다
        """
        input_socket, (client_ip, port) = client_request
        print(f"IP:{client_ip},포트번호:{port}에서 접속을 요청했습니다...")
        if signal := input_socket.recv(BUF_SIZE):
            if signal == SECRET_CODE:
                inspect_code = self.inspect_code_generator()  # inspect_code 생성 (1)
                self.inspect_code = inspect_code
                input_socket.sendall(inspect_code)
            else:
                rejection_message = (
                    f"IP: {client_ip}, 포트번호:{port}로 접속을 시도하고 있는것을 확인했습니다."
                    + "요청 암호가 잘못되었습니다. 접속을 거부합니다."
                ).encode("utf-8")
                input_socket.sendall(rejection_message)
                raise ConnectionResetError from Exception(rejection_message)
        else:
            raise ConnectionResetError from Exception("요청 소켓에 데이터가 없습니다")
        print("접속이 허용되었습니다")
        return client_request

    def socket_inspect_processing(self, client_request):
        """
        두번째 소켓으로 받은 inspect_code를 확인합니다.
        올바른 요청인 경우 소켓으로 SECRET_CODE를 보내고 소켓을 반환합니다
        """
        response_socket, (client_ip, port) = client_request
        print(f"두번째 소켓 IP:{client_ip},포트번호:{port}에서 통신망 구축 신호를 받는중입니다...")
        if signal := response_socket.recv(BUF_SIZE):
            if self.inspect_code == signal:  # inspect_code 사용 (2)
                response_socket.sendall(SECRET_CODE)
            else:  #! 이렇게 하지 말고 따로 컨테이너에 넣은다음에 짝 맞춰
                error_message = (
                    f"IP: {client_ip}, 포트번호:{port}의 연결 요청을 처리하는 중에 문제가 발생했습니다."
                    + "발신 소켓 생성용 요청의 검사 코드가 잘못되었습니다."
                ).encode("utf-8")
                response_socket.sendall(error_message)
                raise ConnectionResetError from Exception(error_message)
        else:
            raise ConnectionResetError from Exception("요청 소켓에 데이터가 없습니다")
        print("통신망 구축이 허용되었습니다")
        return client_request


server = Server()
server.open()