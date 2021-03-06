import socket, time, sys,os

BUF_SIZE: int = 4096

class ConnectionExceptions(Exception):
    pass

def make_socket(server_ip:str,server_response_port:str):
    """ 소켓을 생성하고 주소와 포트번호로 connet한다 """
    sock = socket.socket()
    try:
        sock.connect((server_ip,int(server_response_port)))
    except:
        print('서버ip 혹은 포트번호가 잘못되었습니다.')
        raise ConnectionExceptions
    return sock

def send_inspect_code(sock,inspect_code:str):
    sock.sendall(inspect_code.encode('utf-8'))

def communication(sock,secret_code:str):
    """ while True 루프를 돌면서 메세지 수신과 디스플레이 기능을 수행한다"""
    secret_code = secret_code.encode('utf-8')
    try:
        while True:
            msg = sock.recv(BUF_SIZE).decode()
            print(msg)
            sock.sendall(secret_code)
    except:
        raise ConnectionExceptions

notice = ("\n\n\n이 콘솔은 디스플레이 스크린입니다.\n\n\n")

if __name__ == "__main__":
    script, server_ip, server_input_port, server_response_port, secret_code,inspect_code = sys.argv
    try:
        sock = make_socket(server_ip,server_response_port)
        send_inspect_code(sock,inspect_code)
        communication(sock,secret_code)
    except ConnectionExceptions:
        print("[에러] 서버와 연결을 시도하다가 문제가 발생했습니다.\n"
        +"----------예상 원인----------\n"
        +"(1)암호 인증 실패\n"
        +"(2)서버 사라짐\n"
        +"-----------------------------\n"
        )
        input('확인(enter)')


