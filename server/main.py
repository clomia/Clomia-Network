import socket, random, os, sys, time

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from threading import Thread, Lock
from queue import Queue
from itertools import cycle
from typing import Tuple, Callable
from korean_name_generator import namer
from env import (
    SERVER_PRIVATE_IP,
    OPEN_PORT_LIST,
    BUF_SIZE,
    SECRET_CODE,
    SOCKET_QUEUE_SIZE,
    SERVER_DATA_QUEUE_SIZE,
    INSPECT_CODE_RANGE,
    BINDING_SOCKET_QUEUE_SIZE,
)

# ? 데이터는 모두 bytes로 다룬다. 로그 찍을때만 인코딩한다
# ? 단, 생성의 경우 str으로 유지한다. 최종 단계에서 한번에 인코딩한다
# ? 닫힌소켓은 죽이자. 클라이언트가 없는데 있을 필요가 없어
#! encode, socket에 인자 넣어


def remove_socket(sock, error_message=""):
    sock.close()
    del sock
    print(f"{error_message}\n:소켓을 제거하였습니다.")


now = lambda: time.strftime("(%m/%d) %H시 %M분 %S초|")


class SendallMethodException(Exception):
    """ sendall 메서드로 데이터를 전송하다가 raise되는 예외입니다"""

    def __init__(self):
        super().__init__("sendall 메서드로 데이터를 전송하는것에 실패했습니다")


class RecvMethodException(Exception):
    """
    recv 메서드가 아무런 데이터도 수신하지 못하거나 예외를 발생시킬때 raise되는 예외입니다.
    SECRET_CODE(암호)를 수신했지만 SECRET_CODE(암호)가 맞지 않을 때도 raise됩니다
    """

    def __init__(self):
        super().__init__("recv 메서드가 아무런 데이터도 수신하지 못하였습니다")


class ResponseSocket(Thread):
    """ 응답용 소켓을 관리한다 """

    def __init__(self, sock_data: Tuple[socket.socket, Tuple[str, int]], welcome_message):
        """ sock_data매개변수는 소켓객체가 아니라는 점에 유의 """
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.lock = Lock()
        # 타겟 클라이언트 전용 데이터 큐 (데이터 큐 파이프라인의 출력부분)
        self.transmit_queue = Queue(SOCKET_QUEUE_SIZE)
        self.welcome_message = welcome_message

    def send(self, data: bytes):
        """ 데이터를 입력받아서 전송 데이터 큐에 넣는다 """
        self.transmit_queue.put(data)

    def run(self):
        """ 전송 데이터 큐에 데이터가 들어오는데로 데이터를 전송한다 """
        self.sock.sendall(self.welcome_message)
        try:
            while True:
                # * Blocking
                if SECRET_CODE == self.sock.recv(BUF_SIZE):  # 처음꺼는연결 구축신호(SECRET_CODE)
                    with self.lock:
                        # * Blocking
                        data: bytes = self.transmit_queue.get()
                        try:
                            self.sock.sendall(data)
                        except ConnectionResetError:
                            raise SendallMethodException
                else:
                    raise RecvMethodException
        except RecvMethodException:
            # 클라이언트의 수신용 소켓이 사라짐
            remove_socket(self.sock, f"{now()}클라이언트의 수신용 소켓이 보낸 SECRET_CODE가 잘못되었습니다.")
        except ConnectionResetError:
            remove_socket(self.sock, f"{now()}입력 대기중에 클라이언트가 사라졌습니다 ")
        except SendallMethodException as e:
            remove_socket(self.sock, f"{now()}{e}")


class InputSocket(Thread):
    """ 입력용 소켓을 관리한다 """

    def __init__(
        self,
        sock_data: Tuple[socket.socket, Tuple[str, int]],
        data_queue: Queue,
        unique_prefix: str,
    ):
        """ sock_data매개변수는 소켓객체가 아니라는 점에 유의 """
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.unique_prefix = unique_prefix
        self.data_queue = data_queue
        self.lock = Lock()

    def run(self):
        """ 클라이언트로 부터 받은 데이터를 서버의 데이터 큐에 넣는다 """
        try:
            while True:
                # * Blocking
                if data := self.sock.recv(BUF_SIZE):
                    data = (now() + self.unique_prefix).encode("utf-8") + data
                    with self.lock:
                        self.data_queue.put(data)
                        try:
                            self.sock.sendall(SECRET_CODE)
                        except ConnectionResetError:
                            raise SendallMethodException
                else:
                    raise RecvMethodException
        except RecvMethodException:
            # 클라이언트의 발신용 소켓이 사라짐
            remove_socket(self.sock, f"{now()}클라이언트로부터 받은 데이터가 없습니다")
        except ConnectionResetError:
            remove_socket(self.sock, f"{now()}입력 대기중에 클라이언트가 사라졌습니다 ")


class Connection(Thread):
    """ 클라이언트와의 연결을 관리한다 ResponseSocket(응답 객체)과 InputSocket(입력 객체)의 상위 노드이다 """

    _counter = 0

    def __init__(
        self,
        input_socket_data: Tuple[socket.socket, Tuple[str, int]],
        response_socket_data: Tuple[socket.socket, Tuple[str, int]],
        data_queue: Queue,
    ):
        """ 입력용 소켓과 응답용 소켓을 묶어서 클라이언트 연결 관리자를 생성한다 """
        super().__init__()
        Connection._counter += 1
        self.gender_cycle = cycle((False, True))  # AI가 이름을 작명할때 여자이름,남자이름을 반복하도록
        self.client_name = namer.generate(next(self.gender_cycle))
        self.input_socket_data = input_socket_data
        self.data_queue = data_queue
        self.lock = Lock()
        self.pk = Connection._counter
        self.unique_prefix = f"ID{self.pk}|{self.client_name}: "
        welcome_message = (
            f"입장 시간: {now()[:-5]}\nID: {self.pk}\n"
            + f"AI가 작명한 이름 : {self.client_name}\n"
            + f"\n{self.client_name}님 환영합니다. 이 콘솔창은 디스플레이로 사용됩니다.\n"
            + "디스플레이에 어떠한 입력도 하지 마십시오.\n\n"
        ).encode("utf-8")
        self.response_thread = ResponseSocket(response_socket_data, welcome_message)
        self.input_thread = InputSocket(self.input_socket_data, self.data_queue, self.unique_prefix)

    def run(self):
        """ 입력 쓰레드와 응답 쓰레드를 실행한다"""
        self.input_thread.start()
        self.response_thread.start()
        self.input_thread.join()
        self.response_thread.join()
        # * Blocking # ! 두 쓰레드는 문제가 생기면 while을 빠져나와 종료하라 그러면 알아서 여기로 도달하게되고 이 아래에서 뒤처리를 한다
        notice = f"\n{now()}안내 메시지: {self.client_name} 님이 없어졌습니다.\n"
        print(
            notice,
            f"\n{now()}{self.unique_prefix} : 탈주를 확인했습니다. 관련 소켓들이 모두 제거되었으며 해당 Connection쓰레드를 종료합니다",
        )
        with self.lock:
            self.data_quene.put(notice.encode("utf-8"))

    def send(self, response_data: bytes):
        """ 바로 아래 노드의 응답 쓰레드 전송 큐로 데이터를 전달한다."""
        # * Blocking. send 대기중
        self.response_thread.send(response_data)


class Server:
    """ 수많은 접속(Connection)을 관리한다 Connection의 상위 노드이다 """

    def __init__(self):
        # todo Queue를 상속받아서 로깅 메서드 정의
        self.data_queue = Queue(SERVER_DATA_QUEUE_SIZE)
        self.inspect_code_generator: Callable[[], bytes] = lambda: str(
            random.randint(*INSPECT_CODE_RANGE)
        ).encode("utf-8")
        self.connection_threads = []
        self.socket_mapping = {}
        self.binding_socket_queue = Queue(BINDING_SOCKET_QUEUE_SIZE)
        self.lock = Lock()

    def main_processing_loop(self):
        """ 데이터 큐에 데이터가 들어오면 그것을 모든 클라이언트에게 전송하는 루프 = 대화를 담당"""
        while True:
            data = self.data_queue.get()  # * Blocking
            print(f"{now()}데이터 큐에 데이터가 들어왔습니다. 모든 클라이언트에게 전송합니다\n Data: {data.decode()}\n")
            for thread in self.connection_threads:
                thread.send(data)

    def connection_generation_loop(self):
        """ 클라이언트의 요청이 들어오는대로 커넥션 쓰레드를 생성,실행하는 루프 = 연결 구축을 담당"""
        Thread(target=self.input_socket_mapping_loop).start()
        Thread(target=self.binding_two_socket_loop).start()
        while True:
            input_socket_data, response_socket_data = self.binding_socket_queue.get()  # * Blocking
            thread = Connection(input_socket_data, response_socket_data, self.data_queue)
            self.connection_threads.append(thread)
            client_name = thread.client_name
            _, (input_socket_ip, input_socket_port) = input_socket_data
            _, (response_socket_ip, response_socket_port) = response_socket_data
            print(
                f"\n{now()}연결이 성공적으로 구축되었습니다. 클라이언트 이름: {client_name}\n"
                + f"입력 소켓과 대응되는 클라이언트의 발신 소켓: IP: {input_socket_ip}, Port: {input_socket_port}\n"
                + f"응답 소켓과 대응되는 클라이언트의 수신 소켓: IP: {response_socket_ip}, Port: {response_socket_port}\n"
            )
            thread.start()

    def input_socket_mapping_loop(self):
        """ 입력 소켓을 인스팩트코드와 매핑시켜서 (socket_mapping에)저장하는 루프이다"""
        while True:
            input_socket_data = self.input_socket_generator()  # * Blocking
            print(f"{now()}인스팩트 코드를 생성한뒤 클라이언트로 발송하였습니다. 인스팩트 코드 : {self.inspect_code}")
            with self.lock:
                self.socket_mapping[self.inspect_code] = input_socket_data
            print(f"{now()}인스팩트 코드를 발송한 후 회신을 대기중인 입력 소켓 목록\n=>{self.socket_mapping}\n대기중입니다...")

    def binding_two_socket_loop(self):
        """ 응답 소켓으로 수신한 인스팩트 코드와 매핑되는 입력 소켓을 찾은 뒤 두 소켓을 묶어서 큐(binding_socket_queue)에 넣는다"""
        while True:
            response_socket_data = (
                self.connection_establish_attempt_request_listener()
            )  # * Blocking
            response_socket, (ip, port) = response_socket_data
            try:
                inspect_code = response_socket.recv(BUF_SIZE)
            except ConnectionResetError:
                remove_socket(self.sock, f"{now()}입력대기중에 클라이언트가 사라졌습니다 ")
            print(
                f"{now()}[회신을 받았습니다]연결 구축 요청 : IP: {ip} , Port: {port}, 인스팩트 코드: {inspect_code} --- 응답 소켓이 생성되었습니다"
            )
            with self.lock:
                if inspect_code:
                    input_socket_data = self.socket_mapping[inspect_code]
                else:
                    raise RecvMethodException  # ?인스팩트 코드를 못받아서 Key로 사용 불가능 (클라이언트 문제라고 생각)
                self.binding_socket_queue.put((input_socket_data, response_socket_data))
            print(
                f"{now()}{inspect_code}를 키로 사용해 짝을 이루는 입력소켓을 찾았습니다. 두 소켓을 묶어서 binding_socket_queue(큐)에 넣었습니다"
            )

    def connection_establish_attempt_request_listener(
        self,
    ) -> Tuple[socket.socket, Tuple[str, int]]:
        """ 연결 구축 시도 요청을 받아서 반환한다"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((SERVER_PRIVATE_IP, self.response_port))
            server_socket.listen(SOCKET_QUEUE_SIZE)
            connection_establish_attempt_request = server_socket.accept()  # * Blocking
            return connection_establish_attempt_request

    def input_socket_generator(self) -> Tuple[socket.socket, Tuple[str, int]]:
        """ 이 함수가 실행될때 self.inspect_code가 갱신된다 """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((SERVER_PRIVATE_IP, self.input_port))
            server_socket.listen(SOCKET_QUEUE_SIZE)
            connection_approval_request = server_socket.accept()  # * Blocking
            input_socket_data = self.connection_requests_processing(connection_approval_request)
            return input_socket_data

    def connection_requests_processing(
        self, client_request: Tuple[socket.socket, Tuple[str, int]]
    ) -> Tuple[socket.socket, Tuple[str, int]]:
        """
        소켓으로 받은 SECRET_CODE를 확인합니다.
        inspect_code를 생성해서 self.inspect_code를 갱신합니다
        올바른 요청인 경우 소켓으로 inspect_code를 보내고 소켓을 반환합니다
        """
        input_socket, (client_ip, port) = client_request
        print(f"{now()}IP:{client_ip},포트번호:{port}에서 접속을 요청했습니다. 입력 소켓이 생성되었습니다.")
        try:
            if secret_code := input_socket.recv(BUF_SIZE):
                if secret_code == SECRET_CODE:
                    inspect_code = self.inspect_code_generator()  # inspect_code 생성 (1)
                    self.inspect_code = inspect_code
                    try:
                        input_socket.sendall(inspect_code)
                    except ConnectionResetError:
                        raise SendallMethodException
                    print(f"{now()}암호가 확인되었습니다.")
                else:
                    rejection_message = (
                        f"{now()}IP: {client_ip}, 포트번호:{port}로 접속을 시도하고 있는것을 확인했습니다. 요청 암호가 잘못되었습니다. 접속을 거부합니다. "
                    ).encode("utf-8")
                    try:
                        input_socket.sendall(rejection_message)
                    except ConnectionResetError:
                        raise SendallMethodException
            else:
                raise RecvMethodException
            return client_request
        except ConnectionResetError:
            remove_socket(self.sock, f"{now()}입력대기중에 클라이언트가 사라졌습니다 ")
        except SendallMethodException as e:
            remove_socket(self.sock, f"{now()}{e}")
        except RecvMethodException as e:
            remove_socket(self.sock, f"{now()}{e}")

    def open(self, input_port, response_port):
        self.input_port = input_port
        self.response_port = response_port
        print(f"{now()}서버가 실행되었습니다. -- 입력용 포트번호: {input_port} , 응답용 포트번호: {response_port}")
        set_up_connection_thread = Thread(target=self.connection_generation_loop)
        main_connection_thread = Thread(target=self.main_processing_loop)
        set_up_connection_thread.start()
        main_connection_thread.start()


server = Server()
server.open(*OPEN_PORT_LIST[0:2])