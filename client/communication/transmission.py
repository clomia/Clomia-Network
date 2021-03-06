import socket, time, sys,os

PATH: str = os.path.dirname(os.path.realpath("transmission"))+'/communication'
BUF_SIZE: int = 4096
INSPECT_CODE_RANGE: tuple = (10000, 100000)

class ConnectionExceptions(Exception):
    pass

def make_socket(server_ip:str,server_input_port:str):
    """ 소켓을 생성하고 주소와 포트번호로 connet한다 """
    sock = socket.socket()
    try:
        sock.connect((server_ip,int(server_input_port)))
    except:
        print('서버ip 혹은 포트번호가 잘못되었습니다.')
        raise ConnectionExceptions
    return sock

def recv_inspect_code(sock,secret_code:str) -> str:
    """ 서버로 암호를 전송 한 뒤 인스팩트 코드를 받아서 인스팩트 코드(str)를 반환한다. """
    secret_code = secret_code.encode('utf-8')
    try:
        sock.sendall(secret_code)
        inspect_code = sock.recv(BUF_SIZE).decode()
        _min,_max = INSPECT_CODE_RANGE
        if not (_min <= int(inspect_code) < _max):
            raise Exception
    except:
        raise ConnectionExceptions
    return inspect_code

def communication(sock):
    """ while True 루프를 돌면서 사용자 입력과 발신 기능을 수행한다"""
    try:
        while True:
            msg = input('>>> ').encode('utf-8')
            sock.sendall(msg)
            sock.recv(BUF_SIZE)
    except:
        raise ConnectionExceptions

notice = ("\n\n\n이 콘솔은 메세지 입력창으로 사용됩니다.\n\n\n")

if __name__ == "__main__":
    script, server_ip, server_input_port, server_response_port, secret_code = sys.argv
    try:
        sock = make_socket(server_ip,server_input_port)
        inspect_code = recv_inspect_code(sock,secret_code)
        os.system(
            f"start cmd /k {PATH}/receiving.py {server_ip} {server_input_port} {server_response_port} {secret_code} {inspect_code}"
        )
        print(notice)
        time.sleep(1) #서버가 connection을 구축하기 위한 여유시간
        print('메세지를 입력해주세요.\n\n')
        communication(sock)
    except ConnectionExceptions:
        print("[에러] 서버와 연결을 시도하다가 문제가 발생했습니다.\n"
        +"----------예상 원인----------\n"
        +"(1)암호 인증 실패\n"
        +"(2)서버 사라짐\n"
        +"-----------------------------\n"
        )
        input('확인(enter)')


