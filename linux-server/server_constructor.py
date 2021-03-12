import socket,random,os,sys,time
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname("server_constructor"))))
from urllib import parse
from itertools import cycle
from queue import Queue
from threading import Lock, Thread
from typing import List, Tuple, Callable, NoReturn
from korean_name_generator import namer
from http_manager import template_mapping,http_method,request_verification
from terminal import get_external_ip

#------------- env -------------
# ? 네트워크 버퍼 크기랑 잘 맞는 2의 거듭제곱으로 설정
BUF_SIZE: int = 4096
# ? 응답 소켓 객체와 서버소켓의 큐 사이즈 (많아봤자 5글자 숫자)
SOCKET_QUEUE_SIZE: int = 40
# ? 클라이언트에서 오는 모든 데이터가 입력되는 큐 사이즈
SERVER_DATA_QUEUE_SIZE: int = 200
# ? 입력 소켓과 응답 소켓이 묶이자마자 들어가는 큐 사이즈
BINDING_SOCKET_QUEUE_SIZE: int = 40
# ? (초단위)입력소켓과 응답소켓이 묶일때까지 기다려줄수 있는 최대 시간
MAPPING_TIME_OUT: int = 2
HTTP_METHOD_LIST = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"]
INSPECT_CODE_RANGE: Tuple[int, int] = (10000, 100000)
#-----------------------------------------------


now: Callable[[], str] = lambda: time.strftime("(%m/%d) %H시 %M분 %S초|")
socket_data = Tuple[socket.socket, Tuple[str, int]]

def remove_socket(sock, error_message=""):
    sock.close()
    del sock
    print(f"{error_message}\n:소켓을 제거하였습니다.")


class SendallMethodException(Exception):
    """ sendall 메서드로 데이터를 전송하다가 raise되는 예외입니다"""

    def __init__(self) -> NoReturn:
        super().__init__("sendall 메서드로 데이터를 전송하는것에 실패했습니다")


class RecvMethodException(Exception):
    """
    recv 메서드가 아무런 데이터도 수신하지 못하거나 예외를 발생시킬때 raise되는 예외입니다.
    SECRET_CODE(암호)를 수신했지만 SECRET_CODE(암호)가 맞지 않을 때도 raise됩니다
    """

    def __init__(self) -> NoReturn:
        super().__init__("recv 메서드가 아무런 데이터도 수신하지 못하였습니다")


class ResponseSocket(Thread):
    """ 응답용 소켓을 관리한다 """

    def __init__(self, sock_data: socket_data, secret_code: bytes, welcome_message: bytes, server_name: str):
        """ sock_data매개변수는 소켓객체가 아니라는 점에 유의 """
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.sock.settimeout(1000)
        # 타겟 클라이언트 전용 데이터 큐 (데이터 큐 파이프라인의 출력부분)
        self.transmit_queue = Queue(SOCKET_QUEUE_SIZE)
        self.welcome_message = welcome_message
        self.secret_code = secret_code
        self.server_name = server_name

    def send(self, data: bytes):
        """ 데이터를 입력받아서 전송 데이터 큐에 넣는다 """
        self.transmit_queue.put(data)

    def run(self):
        """ 전송 데이터 큐에 데이터가 들어오는데로 데이터를 전송한다 """
        self.sock.sendall(self.welcome_message)
        try:
            while True:
                # * Blocking
                if self.secret_code == self.sock.recv(BUF_SIZE):
                    data: bytes = self.transmit_queue.get()  # * Blocking
                    try:
                        self.sock.sendall(data)
                    except ConnectionResetError:
                        raise SendallMethodException
                else:
                    raise RecvMethodException
        except RecvMethodException:
            # 클라이언트의 수신용 소켓이 사라짐
            print(f'암호 대신 받은것: {self.secret_code}')
            remove_socket(
                self.sock, f"{self.server_name}{now()}클라이언트의 수신용 소켓이 보낸 SECRET_CODE가 잘못되었습니다.")
        except ConnectionResetError:
            remove_socket(
                self.sock, f"{self.server_name}{now()}입력 대기중에 클라이언트가 사라졌습니다 ")
        except SendallMethodException as e:
            remove_socket(self.sock, f"{self.server_name}{now()}{e}")
        except socket.timeout:
            remove_socket(
                self.sock, f"{self.server_name}{now()}소켓의 대기시간이 만료되었습니다 ")


class InputSocket(Thread):
    """ 입력용 소켓을 관리한다 """

    def __init__(
        self,
        sock_data: socket_data,
        data_queue: Queue,
        unique_prefix: str,
        secret_code: bytes,
        server_name: str,
    ):
        """ sock_data매개변수는 소켓객체가 아니라는 점에 유의 """
        super().__init__()
        self.sock, (self.client_ip, self.client_port) = sock_data
        self.sock.settimeout(1000)
        self.unique_prefix = unique_prefix
        self.data_queue = data_queue
        self.lock = Lock()
        self.secret_code = secret_code
        self.server_name = server_name

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
                        self.sock.sendall(self.secret_code)
                    except ConnectionResetError:
                        raise SendallMethodException
                else:
                    raise RecvMethodException
        except RecvMethodException:
            # 클라이언트의 발신용 소켓이 사라짐
            remove_socket(
                self.sock, f"{self.server_name}{now()}클라이언트로부터 받은 데이터가 없습니다")
        except ConnectionResetError:
            remove_socket(
                self.sock, f"{self.server_name}{now()}입력 대기중에 클라이언트가 사라졌습니다 ")
        except socket.timeout:
            remove_socket(
                self.sock, f"{self.server_name}{now()}소켓의 대기시간이 만료되었습니다 ")


class Connection(Thread):
    """ 클라이언트와의 연결을 관리한다 ResponseSocket(응답 객체)과 InputSocket(입력 객체)의 상위 노드이다 """

    _counter = 0

    def __init__(
        self,
        input_socket_data: socket_data,
        response_socket_data: socket_data,
        data_queue: Queue,
        server,
        secret_code: bytes,
    ):
        """ 입력용 소켓과 응답용 소켓을 묶어서 클라이언트 연결 관리자를 생성한다 """
        super().__init__()
        Connection._counter += 1
        # AI가 이름을 작명할때 여자이름,남자이름을 반복하도록
        self.gender_cycle = cycle((False, True))
        self.client_name = namer.generate(next(self.gender_cycle))
        self.input_socket_data = input_socket_data
        self.data_queue = data_queue
        self.lock = Lock()
        self.pk = Connection._counter
        self.unique_prefix = f"ID{self.pk}|{self.client_name}: "
        welcome_message = (
            '\n'+"-"*40+"\n"
            + f'브라우저로 접속할때는 아래의 URL을 사용하면 됩니다.\n{server.private_ip}:{server.response_port}\n'+'-'*40+'\n\n'
            + f"접속한 서버 이름: {server.name}\n"
            + f"입장 시간: {now()[:-5]}\nID: {self.pk}\n"
            + f"AI가 작명한 당신의 이름 : {self.client_name}\n"
            + f"\n{self.client_name}님 환영합니다. 이 화면은 스크린 콘솔입니다.\n"
            +"-"*40+"\n"
        ).encode("utf-8")
        self.secret_code = secret_code
        self.response_thread = ResponseSocket(
            response_socket_data, self.secret_code, welcome_message, server.name)
        self.input_thread = InputSocket(
            self.input_socket_data, self.data_queue, self.unique_prefix, self.secret_code, server.name)
        self.server = server

    def run(self):
        """ 입력 쓰레드와 응답 쓰레드를 실행한다"""
        self.input_thread.start()
        self.response_thread.start()
        self.response_thread.join()
        self.input_thread.join()
        #! 클라이언트 측에서는 수신,발신 소켓을 모두 끊어야 한다
        # * Blocking # ! 두 쓰레드는 문제가 생기면 while을 빠져나와 종료하라 그러면 알아서 여기로 도달하게되고 이 아래에서 뒤처리를 한다
        with self.lock:
            self.server.user_count -= 1
        notice = f"\n[정보]서버명:{self.server.name}{now()}안내 메시지: {self.client_name} 님이 없어졌습니다.\n현재 인원수: {self.server.user_count}\n"
        print(
            notice,
            f"\n{now()}{self.unique_prefix}탈주를 확인했습니다. 관련 소켓들이 모두 제거되었으며 해당 Connection쓰레드를 종료합니다",
        )
        with self.lock:
            self.data_queue.put(notice.encode("utf-8"))

    def send(self, response_data: bytes):
        """ 바로 아래 노드의 응답 쓰레드 전송 큐로 데이터를 전달한다."""
        # * Blocking. send 대기중
        self.response_thread.send(response_data)


class SocketMappingDict(dict):
    def repr_supporter(self, inspect_code_obj, sock: socket_data):
        is_closed = "[닫힘]" if sock[0]._closed else ""  # 닫힘을 볼 일이 없어야 함
        ip = sock[1][0]
        port = sock[1][1]
        return f"{repr(inspect_code_obj)}:<socket {is_closed}IP={ip} , Port={port}>"

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        with Lock():
            keys = tuple(self.keys())
            now_time = time.time()
            for inspect_code_obj in keys:  # !!!!!!!!!
                mapping_waiting_time = now_time - inspect_code_obj.created_time
                if self[inspect_code_obj][0]._closed or mapping_waiting_time > MAPPING_TIME_OUT:
                    print(
                        f"[SocketMappingDict의 메세지]{self.repr_supporter(inspect_code_obj,self[inspect_code_obj])}가 대기시간을 초과했거나 close되어서 제거하였습니다"
                    )
                    #! 이슈 - 깃헙에 올림
                    super().__delitem__(inspect_code_obj)

    def __repr__(self) -> str:
        info_str = "<SocketMappingDict {"
        for key, value in self.items():
            info_str += self.repr_supporter(key, value) + " ,"
        info_str += "}>"
        return info_str


class InspectCode:
    def __init__(self, integer):
        self.inspect_code = str(integer).encode("utf-8")
        self.created_time = time.time()

    def __repr__(self) -> str:
        return f"<InspectCode (inspect_code={self.inspect_code},created_time={repr(self.created_time).split('.')[0]})>"


class InspectCodeValidationError:
    pass


class RecordingQueue(Queue):
    def __init__(self, maxsize, name):
        super().__init__(maxsize)
        self.name = name

    def put(self, item, block=True, timeout=None):
        super().put(item, block, timeout)
        now_date = time.strftime("%Y년%m월%d일")
        msg = item.decode() 
        log_path = os.path.dirname(os.path.realpath("server_constructor")) + "/log"
        file_list = os.listdir(log_path)
        mode = "a" if f"서버명[{self.name}]({now_date}).txt" in file_list else "w"
        with open(log_path + f"/서버명[{self.name}]({now_date}).txt", mode, encoding="utf-8") as file:
            file.write(msg + "\n")


class Server:
    """ 수많은 접속(Connection)을 관리한다 Connection의 상위 노드이다 """

    def __init__(self, name, private_ip, secret_code):
        self.private_ip: str = private_ip
        self.secret_code: bytes = secret_code
        self.lock = Lock()
        self.data_queue = RecordingQueue(SERVER_DATA_QUEUE_SIZE, name)
        self.inspect_code_obj_generator: Callable[[], bytes] = lambda: InspectCode(
            random.randint(*INSPECT_CODE_RANGE)
        )
        self.connection_threads = []
        self.socket_mapping = SocketMappingDict()
        self.binding_socket_queue = Queue(BINDING_SOCKET_QUEUE_SIZE)
        self.name: str = name
        self.user_count = 0

    def main_processing_loop(self):
        """ 데이터 큐에 데이터가 들어오면 그것을 모든 클라이언트에게 전송하는 루프 = 대화를 담당"""
        while True:
            data = self.data_queue.get()  # * Blocking
            print(
                f"서버명:{self.name}{now()}데이터 큐에 데이터가 들어왔습니다. 모든 클라이언트에게 전송합니다\n Data: {data.decode()}\n"
            )
            for thread in self.connection_threads:
                thread.send(data)

    def connection_generation_loop(self):
        """ 클라이언트의 요청이 들어오는대로 커넥션 쓰레드를 생성,실행하는 루프 = 연결 구축을 담당"""
        Thread(target=self.input_socket_mapping_loop).start()
        Thread(target=self.binding_two_socket_loop).start()
        while True:
            input_socket_data, response_socket_data = self.binding_socket_queue.get()  # * Blocking
            thread = Connection(input_socket_data, response_socket_data,
                                self.data_queue, self, self.secret_code)
            self.connection_threads.append(thread)
            client_name = thread.client_name
            _, (input_socket_ip, input_socket_port) = input_socket_data
            _, (response_socket_ip, response_socket_port) = response_socket_data
            print(
                f"\n서버명:{self.name}{now()}연결이 성공적으로 구축되었습니다. 클라이언트 이름: {client_name}\n"
                + f"입력 소켓과 대응되는 클라이언트의 발신 소켓: IP: {input_socket_ip}, Port: {input_socket_port}\n"
                + f"응답 소켓과 대응되는 클라이언트의 수신 소켓: IP: {response_socket_ip}, Port: {response_socket_port}\n"
            )
            self.user_count += 1
            self.data_queue.put(f"\n[정보] {client_name} 님이 입장했습니다. 현재 인원수: {self.user_count}\n".encode('utf-8'))
            thread.start()

    def input_socket_mapping_loop(self):
        """ 입력 소켓을 인스팩트코드와 매핑시켜서 (socket_mapping에)저장하는 루프이다"""
        while True:
            input_socket_data = self.input_socket_generator()  # * Blocking
            if not input_socket_data:
                continue
            print(
                f"서버명:{self.name}{now()}인스팩트 코드를 생성한뒤 클라이언트로 발송하였습니다. 인스팩트 코드 : {self.inspect_code_obj.inspect_code}"
            )
            with self.lock:
                self.socket_mapping[self.inspect_code_obj] = input_socket_data
            print(
                f"서버명:{self.name}{now()}인스팩트 코드를 발송한 후 회신을 대기중인 입력 소켓 목록\n=>{self.socket_mapping}\n대기중입니다..."
            )

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
                try:
                    remove_socket(self.sock, f"{now()}입력대기중에 클라이언트가 사라졌습니다 ")
                    continue
                except:
                    continue
            print_inspect_code = "형식에 맞지 않음" if len(inspect_code) > 5  else inspect_code
            print(
                f"서버명:{self.name}{now()}[회신을 받았습니다]연결 구축 요청 : IP: {ip} , Port: {port}, 인스팩트 코드: {print_inspect_code}\n: 응답 소켓이 생성되었습니다"
            )
            for inspect_code_obj in tuple(self.socket_mapping.keys()):
                if inspect_code_obj.inspect_code == inspect_code:
                    current_inspect = inspect_code_obj
                    break
            # *--- 이 사이에 다른 쓰레드가 socket_mapping을 참조하면서 소켓 자동제거가 이루어진다 때문에 아래의 로직과 모순되지 않는다
            # 아래의 로직 : 아래의 pop메서드가 index오류를 raise하는 경우도 포함하도록 except를 사용하는 로직
            with self.lock:
                try:
                    input_socket_data = self.socket_mapping.pop(
                        current_inspect)
                except:
                    # 인스팩트 코드가 잘못된 경우 #!(여기서 브라우저의 요청을 구분)
                    if len(inspect_code) <= len(str(INSPECT_CODE_RANGE[0])):
                        print(
                            f"서버명:{self.name}{now()}인스팩트 코드{inspect_code} 와 매칭되는 소켓이 없습니다. 요청을 무시합니다"
                        )
                        continue
                    elif (method := http_method(inspect_code)) in HTTP_METHOD_LIST:
                        http_request = parse.unquote(inspect_code.decode())
                        if not request_verification(http_request):
                            response_socket.close()
                            del response_socket
                            continue
                        if method == "GET":
                            print(
                                f"\n서버명:{self.name}{now()}HTTP 요청 메세지[{method}]를 감지했습니다. HTTP응답으로 회신합니다.\n{http_request}\n"
                            )
                            current_page = template_mapping(http_request)
                            response_socket.sendall(current_page)
                            # http_response(response_socket)
                            response_socket.close()
                            del response_socket
                            continue
                        elif method == "POST":
                            continue
                    else:
                        print(
                            f"서버명:{self.name}{now()}인스팩트 코드도 아니고 HTTP요청도 아닌 알 수 없는 요청을 받았습니다. 무시합니다"
                        )
                        continue
                self.binding_socket_queue.put(
                    (input_socket_data, response_socket_data))
            print(
                f"서버명:{self.name}{now()}{inspect_code}를 키로 사용해 짝을 이루는 입력소켓을 찾았습니다. 두 소켓을 묶어서 binding_socket_queue(큐)에 넣었습니다"
            )

    def connection_establish_attempt_request_listener(
        self,
    ) -> socket_data:
        """ 연결 구축 시도 요청을 받아서 반환한다"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.private_ip, self.response_port))
            server_socket.listen(SOCKET_QUEUE_SIZE)
            connection_establish_attempt_request = server_socket.accept()  # * Blocking
            return connection_establish_attempt_request

    def input_socket_generator(self) -> socket_data:
        """ 이 함수가 실행될때 self.inspect_code_obj가 갱신된다 """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.private_ip, self.input_port))
            server_socket.listen(SOCKET_QUEUE_SIZE)
            connection_approval_request = server_socket.accept()  # * Blocking
            input_socket_data = self.connection_requests_processing(
                connection_approval_request)
            return input_socket_data

    def connection_requests_processing(self, client_request: socket_data) -> socket_data:
        """
        소켓으로 받은 SECRET_CODE를 확인합니다.
        inspect_code_obj를 생성해서 self.inspect_code_obj를 갱신합니다
        올바른 요청인 경우 소켓으로 inspect_code를 보내고 소켓을 반환합니다
        """
        input_socket, (client_ip, port) = client_request
        print(
            f"서버명:{self.name}{now()}IP:{client_ip},포트번호:{port}에서 접속을 요청했습니다. 입력 소켓이 생성되었습니다.")
        try:
            if secret_code := input_socket.recv(BUF_SIZE):
                if secret_code == self.secret_code:
                    self.inspect_code_obj = self.inspect_code_obj_generator()  # inspect_code 생성 (1)
                    try:
                        input_socket.sendall(
                            self.inspect_code_obj.inspect_code)
                    except ConnectionResetError:
                        raise SendallMethodException
                    print(f"서버명:{self.name}{now()}암호가 확인되었습니다.")
                else:
                    rejection_message = (
                        f"서버명:{self.name}{now()}IP: {client_ip}, 포트번호:{port}로 접속을 시도하고 있는것을 확인했습니다. 요청 암호가 잘못되었습니다. 접속을 거부합니다. "
                    )
                    print(rejection_message)
                    input_socket.sendall(rejection_message.encode("utf-8"))
                    raise ConnectionResetError
            else:
                raise RecvMethodException
            return client_request
        except ConnectionResetError:
            remove_socket(
                input_socket, f"서버명:{self.name}{now()}입력대기중에 클라이언트가 사라졌습니다 | 혹은 접속 요청을 받았으나 암호가 잘못되었습니다.")
        except SendallMethodException as e:
            remove_socket(input_socket, f"서버명:{self.name}{now()}{e}")
        except RecvMethodException as e:
            remove_socket(input_socket, f"서버명:{self.name}{now()}{e}")
        return False


    def open(self, input_port: int, response_port: int):
        """ 서버를 실행한다 """
        self.input_port = input_port
        self.response_port = response_port
        external_ip = get_external_ip()
        print(
            f"\n서버명:{self.name}{now()}서버가 실행되었습니다. -- 입력용 포트번호: {input_port} , 응답용 포트번호: {response_port}"
        )
        print('-'*40
            +f'\n인트로 웹 페이지를 아래의 URL로 오픈하였습니다.\n{external_ip}:{self.response_port}/intro\n'
            +'포럼을 비롯한 모든 웹 서비스는 80번 포트(HTTP전용포트)로만 제공할수 있습니다.\n'
            +'[주의]80번 포트가 아니면 인트로 페이지를 제외한 웹 서비스를 제공할 수 없습니다.\n'
            +f'80번 포트가 열려있다면 {external_ip}/intro 로 웹 서비스를 제공합니다.\n' 
            +'-'*40+'\n')
        set_up_connection_thread = Thread(
            target=self.connection_generation_loop)
        main_connection_thread = Thread(target=self.main_processing_loop)
        set_up_connection_thread.start()
        main_connection_thread.start()


if __name__ == '__main__':
    script, *settings = sys.argv
    args = [] # ['50000', '50001', '서버이름' ,'ip' ,'암호']
    for arg_type,arg in zip(cycle(range(5)),settings):
        if arg_type == 0 or arg_type == 1:
            args.append(int(arg))
        elif arg_type == 2 or arg_type == 3:
            args.append(arg)
        else:
            args.append(arg.encode('utf-8'))
            input_port, response_port, name, ip, secret_code = args
            Server(name, ip, secret_code).open(input_port,response_port)
            args.clear()

