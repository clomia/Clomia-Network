import socket, time, sys

if __name__ == "__main__":
    script, *arg = sys.argv
    print(arg)

# + 파일 i/o로 통신 구축이 끝난 발신용 소켓 제공받기
# with


"""
host = "192.168.219.101"
port = 50012
SECRET_CODE = "이것은 암호입니다".encode("utf-8")  #

#!발신용 소켓


def run_client(transmission_socket):
    run(transmission_socket)
    while True:
        msg = input("메세지를 입력하세요:").encode("utf-8")
        transmission_socket.sendall(msg)


def run(transmission_socket):
    transmission_socket.sendall(SECRET_CODE)  # ? 연결 요청[1]
    inspect_code = transmission_socket.recv(1024)  # ? 인스팩트 코드 수신[2]
    print(f"인스팩트 코드는 : {inspect_code.decode()}")
    # 수신용 소켓이 인스팩트 코드를 보내는 순간부터 사용 가능


transmission_socket = socket.socket()
transmission_socket.connect((host, port))

run_client(transmission_socket)
"""
