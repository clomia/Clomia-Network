import socket, time, sys

class ConnectionError(Exception):
    pass

def make_socket(server_ip,server_input_port):
    """ 소켓을 생성하고 주소와 포트번호로 connet한다 """
    sock = socket.socket()
    try:
        sock.connect((server_ip,server_input_port))
    except:
        print('서버ip 혹은 포트번호가 잘못되었습니다.')
        raise ConnectionError
    return sock

def recv_inspect_code():
    """ 서버로 암호를 전송 한 뒤 인스팩트 코드를 받아서 인스팩트 코드를 반환한다. """
    

if __name__ == "__main__":
    script, server_ip, server_input_port, server_response_port, secret_code = sys.argv
    


