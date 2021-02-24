import socket, os, sys

# import 탐색 경로(sys.path)에 상위폴더 절대경로 추가
from threading import Thread, Lock

# ? 멀티 쓰레드가 사용하는 컨테이너이므로 약한 참조로 가비지 관리를 해준다 (각 쓰레드가 self바인딩으로 참조카운터를 하나씩 가진다)
# Set의경우 쓰레드들이 다중참조를 가져서 즉각즉각 가비지 컬렉션이 안되지만 안전장치로 유지중이다
# Dict의 경우 쓰레드가 자살명령을 받아서 루프를 종료한다. 이때 자동으로 Dict에서도 메모리 삭제를 유도하도록 장치했다
from weakref import WeakSet, WeakValueDictionary
from itertools import cycle
from functools import partial
from typing import Callable
from korean_name_generator import namer
from env import SERVER_PRIVATE_IP, PORT_NUMBER, BUF_SIZE


class Server:
    def __init__(self, private_ip, port):
        self.ip = private_ip
        self.port = port
        self.conn_set = WeakSet()
        self.gen_iter = cycle((False, True))
        self.cr_dict = WeakValueDictionary()
        # todo 파일 로그 시스템 만들기

    def run(self):
        with socket.socket() as server_sock:
            server_sock.bind((self.ip, self.port))
            pk = 0
            while key := pk + 1:
                server_sock.listen(1)
                conn_socket, address = server_sock.accept()
                name = namer.generate(next(self.gen_iter))
                unique_name = f"ID{key}|{name}"
                # ? 컨테이너와 리터럴은 약한 참조를 만들수가 없다, partial객체를 사용한다
                ref_setting: Callable = partial(lambda x: x, (conn_socket, unique_name, key))
                self.conn_set.add(ref_setting)
                thread = ClientRepresentative(self, ref_setting, address)
                self.cr_dict[key] = thread
                thread.start()


# PF_INET(IPv4 인터넷 프로토콜)| socket.AF_INET ,   SOCK_STREAM(연결 지향형 소켓)| socket.SOCK_STREAM
class ClientRepresentative(Thread):
    """
    한명한테 받아서 나머지한테 보낸다
    """

    def __init__(self, server: Server, ref_setting: Callable, address: tuple):
        super().__init__(daemon=True)
        # ? 강한 레퍼런스 카운트 1 생성 :> 메모리 청소시 del self.ref_setting
        self.ref_setting = ref_setting
        self.conn_socket, self.unique_name, self.pk = ref_setting()
        self.target_ip, self.port = address
        self.server = server
        self.lock = Lock()
        self.suicide_order = False

    #! recv는 네트워크 버퍼가 비워지면 반환된다, send는 채워지면 반환된다(이것들은 네트워크 버퍼에서 작동한다) I/O블러킹 지점
    def run(self):
        missing_users = []
        while True:
            try:
                data = self.conn_socket.recv(BUF_SIZE)
                # ? 받는 과정에서의 오류
                if not data:
                    raise ConnectionResetError
            except ConnectionResetError:
                self.conn_socket.close()
                self.server.conn_set.remove(self.ref_setting)
                #! 함수로 쪼개서 써야해 1. 수신 실패의 경우, 송신 실패의 경우 <- 다른 클라이언트에 탈주안내 매세지 보내는 함수
                print(self.make_missing_massage(missing_users, message))
                break
            message = f"{self.unique_name}: {data.decode()}"
            if missing_users:
                message = self.make_missing_massage(missing_users, message)
            print(f"발신지: IP = {self.target_ip} , 포트번호 = {self.port}\n{message}\n")
            with self.lock:
                # ! thread병합 참조로 인해서 소켓이 바로 없어지지 않는다, remove ref_setting 필요
                for ref_setting in self.server.conn_set:
                    sock, unique_name, pk = ref_setting()
                    if sock != self.conn_socket:
                        try:
                            sock.sendall(message.encode())
                            # ? 나머지 사람들에게 보내는 과정에서의 에러 헨들링
                        except ConnectionResetError:
                            # ? 통신이 끊긴 클라이언트 처리/소켓 제거
                            sock.close()
                            missing_users.append(unique_name)
                            self.server.cr_dict[pk].suicide_order = True
                            self.server.conn_set.remove(ref_setting)
            if self.suicide_order:
                break

    def make_missing_massage(missing_users, message):
        return f'{" , ".join(missing_users)} 유저가 공간을 떠났습니다.\n{message}'


Server(SERVER_PRIVATE_IP, PORT_NUMBER).run()
