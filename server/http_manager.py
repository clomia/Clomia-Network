import os
import socket
from threading import Thread
from templates import DEFAULT_PAGE,TEMPLATE_MAPPING
from urllib import parse

class TemplateController:
    """
    웹 페이지를 bytes로 직렬화 하기 위해서 html,css,js를 조합하는 메서드를 제공한다
    html,css,js는 하나씩 받으므로 css 와 js를 단일 파일로 작성해야 한다. (복잡한 import는 고려하지 않았다)
    """

    def __init__(self, dir_path):
        """
        현재 위치를 기준으로 html,css,js가 하나씩 들어있는 폴더명을 입력받아서
        html,css,js파일을 모두 읽은뒤 속성으로 할당한다 속성명은 파일 확장자와 같다\n
        html,css,js를 하나의 html파일로 만드는 예시 \n
        main_template = Controller("templates/main")\n
        completed_html = main_template.assembling()
        """
        templates_path = os.path.dirname(os.path.realpath(__file__)) + "/" + dir_path
        file_list = os.listdir(templates_path)
        extension = lambda file_name: file_name.split(".")[1]
        current_extensions = ["html", "css", "js"]
        try:
            for file_name in file_list:
                current_extensions.pop(current_extensions.index(extension(file_name)))
                file_path = templates_path + "/" + file_name
                with open(file_path, "r", encoding="utf-8") as file:  #!뮤텍스 락 필요
                    setattr(self, file_name.split(".")[1], file.read())
        except IndexError:
            raise Exception("폴더 안에 html,css,js파일이 하나씩 있어야 합니다")

    def assembling(self) -> str:
        """ html,css,js를 합쳐서 문자열로 반환한다"""
        decomposition = self.html.split("</head>")
        decomposition[1] = "</head>" + decomposition[1]
        decomposition[0] += '\n<style type="text/css">\n' + self.css + "\n</style>\n"
        css_complete = "".join(decomposition)

        decomposition = css_complete.split("</body>")
        decomposition[1] = "</body>" + decomposition[1]
        decomposition[0] += '\n<script type="text/javascript">\n' + self.js + "\n</script>\n"
        return "".join(decomposition)


class HttpResponse:
    """ 인코딩된 http응답 메시지를 작성해준다."""

    def __init__(self, body):
        self.body = body
        self.start_line = "HTTP/1.1 200 OK\n"
        self.header = "Content-Type: text/html; charset-utf-8\n\n"

    def response_200(self):
        return (self.start_line + self.header + self.body).encode("utf-8")

template_engine = lambda template_dir:HttpResponse(TemplateController(template_dir).assembling()).response_200()

def http_method(http_request:bytes) -> str:
    try:
        return http_request.decode().split(" ")[0]
    except UnicodeDecodeError: #https:// 점미사 헨들링
        return False

def template_mapping(http_request:str) -> bytes:
    """ HTTP GET 요청에 따라 TEMPLATE_MAP에서 올바른 템플릿찾아서 리턴한다"""
    url_path = http_request.split("GET ")[1].split(" HTTP/")[0]
    try:
        return template_engine(TEMPLATE_MAPPING[url_path])
    except KeyError:
        #? url이 잘못되었을 경우 기본으로 DEFAULT_PAGE를 리턴한다
        return template_engine(DEFAULT_PAGE)

def control_database(http_request:str,redirect_template_dir:str) -> bytes:
    """ 
    POST 요청에서 form으로 입력된 정보에 따라 데이터베이스를 조작한다
    데이터베이스를 수정하고 완료 페이지로 이동한다
    """
    url_path = http_request.split("POST ")[1].split(" HTTP/")[0]

class HttpServe(Thread):
    """ 80번 포트로 들어오는 "공식적인" 웹 접속을 처리한다 """
    def __init__(self,private_ip:str):
        super().__init__()
        self.private_ip = private_ip


    def run(self):
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((self.private_ip, 80))
                sock.listen(4096)
                sock, (ip, port) = sock.accept()  # * Blocking
                request_msg = sock.recv(4096)
                method = http_method(request_msg)
                request_msg = request_msg.decode()
                if method == "GET":
                    print(
                        f"\n 80번 포트로 들어온 HTTP 요청 메세지[{method}]를 감지했습니다. HTTP응답으로 웹 페이지를 회신합니다. 페이지: intro\n{request_msg}\n"
                    )
                    current_page = template_mapping(request_msg)
                    sock.sendall(current_page)
                elif method == "POST":
                    a = parse.unquote(request_msg)
                    print(a)
                sock.close()
                continue

HttpServe('192.168.219.102').start()