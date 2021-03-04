import os,socket,pickle,time
from threading import Thread,Lock
from templates import DEFAULT_PAGE,TEMPLATE_MAPPING
from urllib import parse

def set_dir(path) -> str:
    lst = os.listdir(path)
    setting_dir = f'{path}/DB'
    if not 'DB' in lst:
        os.mkdir(setting_dir)
    return setting_dir
PATH = os.path.dirname(os.path.realpath(__file__))
DB_PATH = set_dir(PATH)
DATA_LIST = os.listdir(DB_PATH)

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
                with Lock():
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
    """ 
    GET 요청 처리용 \n
    GET 요청에 따라 TEMPLATE_MAP에서 올바른 템플릿찾아서 리턴한다
    """
    url_path = http_request.split("GET ")[1].split(" HTTP/")[0]
    try:
        return template_engine(TEMPLATE_MAPPING[url_path])
    except KeyError:
        #? url이 잘못되었을 경우 기본으로 DEFAULT_PAGE를 리턴한다
        return template_engine(DEFAULT_PAGE)


#! 게시판 시스템이 하나라서 함수형으로 프로그레밍했다.
#! 대규모의 게시판 시스템을 구성하려면 여기를 리펙토링 하면 된다
def read_db(db_name) -> dict:
    """ 
    읽을 db데이터가 없다면 None이 반환된다
    [중요!!] 쓰레드에서는 반드시 뮤텍스 락을 걸고 함수를 실행해야 한다\n
    """
    
    if f"{db_name}.clomia-db" in DATA_LIST:
        with open(DB_PATH+f"/{db_name}.clomia-db",'rb') as db:
            query_dict = pickle.load(db)
        return query_dict


def apply_forum_html(db_query):
    """ 
    DB로 forum html파일을 렌더링하고 저장한다
    [중요!!] 쓰레드에서는 반드시 뮤텍스 락을 걸고 함수를 실행해야 한다\n
    """
    path = PATH+'/templates/forum/forum.html'
    text_box_gen = lambda text,date_time:f"""
    <div class="text-box">
        <div class="text-box__id">{date_time}</div>
        <div class="text-box__main">
            <p>{text}</p>
        </div>
        <button type="submit" class="del-btn">
            삭제
        </button>
        <form name="delForm" class="del-form display-none" action="/forum" method="post">
            <input type="text" class="delForm__id" name="text_id" placeholder="   글 아이디" />
            <input type="password" class="delForm__password" name="password" placeholder="   비밀번호" />
            <button type="submit" class="del-btn">
                삭제
            </button>
        </form>
    </div>
    """
    with open(path,'r',encoding='utf-8') as file:
        html = file.read()
    text_boxes = ""
    for password,(text,date_time) in db_query.items():
        text_boxes += text_box_gen(text,date_time)
    area = html.split('<!--text-box 시작점-->\n')
    area[0] += ("<!--text-box 시작점-->\n"+text_boxes)
    new_html = ''.join(area)
    with open(path,'w',encoding="utf-8") as file:
        file.write(new_html)


def apply_db(dictionary,db_name) -> str:
    """ 
    딕셔너리를 DB에 세팅한다. DB=딕셔너리가 된다\n
    [중요!!] 쓰레드에서는 반드시 뮤텍스 락을 걸고 함수를 실행해야 한다\n
    데이터베이스 파일 경로를 반환한다
    """
    file_name = f"/{db_name}.clomia-db"
    with open(DB_PATH+file_name,'wb') as db:
        pickle.dump(dictionary,db)
    return DB_PATH+file_name

def extract_query(request):
    """ POST request str에서 쿼리스트링을 딕셔너리로 반환한다"""
    query_strings = request.split("\n")[-1].replace("+", " ").split("&")
    query_dict = {}
    for query in query_strings:
        key, value = query.split("=")
        query_dict[key] = value
    return query_dict




class HttpServe(Thread):
    """ 80번 포트로 들어오는 "공식적인" 웹 접속을 처리한다."""

    def __init__(self,private_ip:str):
        super().__init__()
        self.private_ip = private_ip
        self.lock = Lock()


    def run(self):
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((self.private_ip, 80))
                sock.listen(4096)
                sock, (ip, port) = sock.accept()  # * Blocking
                request_msg = sock.recv(4096)
                method = http_method(request_msg)
                request_msg = parse.unquote(request_msg)
                if method == "GET":
                    print(
                        f"\n 80번 포트로 들어온 HTTP 요청 메세지[{method}]를 감지했습니다. HTTP응답으로 회신합니다.\n{request_msg}\n"
                    )
                    current_page = template_mapping(request_msg)
                    sock.sendall(current_page)
                elif method == "POST":
                    with self.lock:
                        input_query = extract_query(request_msg)
                        db_query = db_query if (db_query := read_db('forum')) else {}
                        ((_,text),(_,password)) = list(input_query.items())
                        now = time.strftime('%Y년 %m월 %d일 %X')
                        db_query[password] = (text,now)
                        apply_db(db_query,'forum')
                        apply_forum_html(db_query)
                        sock.sendall(template_engine(TEMPLATE_MAPPING['/forum']))
                sock.close()
                continue
#! { 비번:(글,date_time) } , 1.신호 받기 2.read_db 3.(가공하기) 4.apply_db 끝!
HttpServe('192.168.219.102').start()
