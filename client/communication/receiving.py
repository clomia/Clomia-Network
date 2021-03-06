import socket


host = "112.158.160.11"
port = 50001
SECRET_CODE = "이것은 암호입니다".encode("utf-8")  #

#! 수신용 소켓


def run_client(receiving_socket):
    run(receiving_socket)
    while True:
        recive(receiving_socket)


receiving_socket = socket.socket()
receiving_socket.connect((host, port))


def run(receiving_socket):
    inspect_code = input("인스펙트 코드 입력:").encode("utf-8")  # !연결 구축 요청[3]
    receiving_socket.sendall(inspect_code)  # 이 순간부터 서버에서 커넥션이 생성되고 쓰레드들이 실행된다


def recive(receiving_socket):
    msg = receiving_socket.recv(1024)
    print(f"메세지 : {msg.decode()}")
    receiving_socket.sendall(SECRET_CODE)


run_client(receiving_socket)

# 인스팩트 코드를 보내는 소캣은 무조건 수신용 소켓이다