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

MY_NAME = ""
PREVIOUS_MESSAGE = f"(00/00) 99시 99분 99초|{MY_NAME}:" #(03/07) 13시 49분 46초|ID4|김미은:
get_name = lambda msg:msg[20:27] # ID4|김미은
get_hour = lambda msg:msg[8:11] # 13시
get_my_name = lambda msg:"ID" + msg.split("ID: ")[1].split("\n")[0] + "|" + msg.split("의 이름 : ")[1][:3] # ID4|김미은

def msg_interface(msg):
    """ 
    서버에서 가공해준 메세지를 한번 더 가공한다
    global변수들을 사용한다
    (info)global에 영향을 미치는 유일한 함수이다.
    """
    global PREVIOUS_MESSAGE
    global MY_NAME
    pure = msg
    if not MY_NAME:
        MY_NAME = get_my_name(msg)
        return msg
    if '\n' in msg:
        return msg
    if get_name(msg) != get_name(PREVIOUS_MESSAGE):
        msg = ('\n'+'-'*40+'\n\n'+msg)
    PREVIOUS_MESSAGE = pure
    return msg


def communication(sock,secret_code:str):
    """ while True 루프를 돌면서 메세지 수신과 디스플레이 기능을 수행한다"""
    secret_code = secret_code.encode('utf-8')
    #try:
    while True:
        data = sock.recv(BUF_SIZE).decode()
        msg = msg_interface(data)
        print(msg)
        sock.sendall(secret_code)
    #except:
        #raise ConnectionExceptions


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


