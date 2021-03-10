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


PATH = os.path.dirname(os.path.realpath('http_manager'))
DB_PATH = set_dir(PATH)
DATA_LIST = os.listdir(DB_PATH)

class TemplateController:
    """
    웹 페이지를 bytes로 직렬화 하기 위해서 html,css,js를 조합하는 메서드를 제공한다
    html,css,js는 하나씩 받으므로 css 와 js를 단일 파일로 작성해야 한다. (복잡한 import는 고려하지 않았다)
    """

    def __init__(self, dir_path,html:str=None,add_js:str=None):
        """
        현재 위치를 기준으로 html,css,js가 하나씩 들어있는 폴더명을 입력받아서
        html,css,js파일을 모두 읽은뒤 속성으로 할당한다 속성명은 파일 확장자와 같다\n
        html,css,js를 하나의 html파일로 만드는 예시 \n
        main_template = Controller("templates/main")\n
        completed_html = main_template.assembling()
        """
        templates_path = os.path.dirname(os.path.realpath('http_manager')) + "/" + dir_path
        file_list = os.listdir(templates_path)
        extension = lambda file_name: file_name.split(".")[1]
        if not html:
            current_extensions = ["html", "css", "js"]
        else :
            current_extensions = ["css", "js"]
        self.add_js = add_js
        try:
            for file_name in file_list:
                try:
                    current_extensions.pop(current_extensions.index(extension(file_name)))
                except ValueError:
                    setattr(self,'html',html)
                    continue
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
        if self.add_js:
            decomposition[0] += ('\n<script type="text/javascript">\n'+ self.add_js +'\n' + self.js + "\n</script>\n")
        else:
            decomposition[0] += ('\n<script>\n'+ self.js + "\n</script>\n")
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
    딕셔너리로로 forum html파일을 작성하고 파일을 저장한다
    그리고 완성한 html 스트링을 리턴한다
    [중요!!] 쓰레드에서는 반드시 뮤텍스 락을 걸고 함수를 실행해야 한다\n
    """
    path = PATH+'/templates/forum/forum.html'
    text_box_gen = lambda text,date_time:f"""
    <div class="text-box">
        <div class="text-box__id">{date_time}</div>
        <div class="text-box__main">
            <p>{text}</p>
        </div>
    </div>
    """
    with open(path,'r',encoding='utf-8') as file:
        html = file.read()
    text_boxes = ""
    for password,(text,date_time) in db_query.items():
        text_boxes = text_box_gen(text,date_time) + text_boxes
    area = html.split('<!--text-box 시작점-->\n')
    clear_html =  area[0] + "<!--text-box 시작점-->\n"
    new_html = clear_html + text_boxes+'</div>' + '<!--<script src="forum.js"></script>--></body></html>'
    with open(path,'w',encoding="utf-8") as file:
        file.write(new_html)
    return new_html


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
    try:
        for query in query_strings:
            key, value = query.split("=")
            if not value and key == 'password':
                query_dict['password'] = str(time.time())
            elif key == "del_password":
                return value
            else :
                query_dict[key] = value
    except ValueError:
        # "\n"이 포함된 본문 처리부분
        sep = request.split('text=')
        if '&password=' in sep[0]:
            text = request.split('text=')[1]
        else:
            text = request.split('text=')[1].split('&password=' )[0]
        query_dict['text'] = text
        query_dict['password'] = str(time.time())
    return query_dict

def request_verification(request_msg:str):
    sources_verifications = [] #하나만 충족하면 된다
    sources_verifications.append(lambda :"GET /intro" in request_msg.split('.')[0])
    sources_verifications.append(lambda :"GET /docs" in request_msg.split('.')[0])
    sources_verifications.append(lambda :"GET /forum" in request_msg.split('.')[0])
    sources_verifications.append(lambda :"POST /forum" in request_msg.split('.')[0] and ("del_password" in request_msg or "password" in request_msg))
    if not (True in [func() for func in sources_verifications]):
        print(f'[요청검사결과 -거부] 요청의 출처가 올바르지 않습니다!!!!!!!!\n---거부한 요청메세지---\n{request_msg}')
        return False
    
    message_verifications = [] #모든 조건을 충족해야 한다
    message_verifications.append(lambda: not ('exec' in request_msg or 'eval' in request_msg))
    message_verifications.append(lambda: "User-Agent" in request_msg)
    message_verifications.append(lambda: not ("chmod" in request_msg))
    message_verifications.append(lambda: request_msg.count("Accept") > 2)
    if False in [func() for func in message_verifications]:
        print(f'[요청검사결과 -거부] 요청메세지에 보안상 의심이 있습니다!!!!!!!!\n---거부한 요청메세지---\n{request_msg}')
        return False
    return True



class HttpServe(Thread):
    """ 80번 포트로 들어오는 "공식적인" 웹 접속을 처리한다."""

    def __init__(self,private_ip:str):
        super().__init__()
        self.private_ip = private_ip
        self.lock = Lock()

    def ignore_to_forum(self,sock):
        """ forum템플릿을 전송하고 소켓을 닫는다 """
        sock.sendall(template_engine(TEMPLATE_MAPPING['/forum']))
        sock.close()
        del sock

    def apply_data(self,db_query,sock,add_js:str = None):
        """ 
        db_query딕셔너리를 db에 적용하고 템플릿을 렌더링 한 뒤에 소켓으로 전송한다
        add_js인자로 js코드가 들어오면 db영향 없이 js코드만 템플릿에 더해서 전송한다.
        """
        apply_db(db_query,'forum')
        html = apply_forum_html(db_query)
        template_dir = TEMPLATE_MAPPING['/forum']
        template = HttpResponse(TemplateController(template_dir,html,add_js).assembling()).response_200()
        sock.sendall(template)

    def run(self):
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((self.private_ip, 80))
                sock.listen(4096)
                sock, (ip, port) = sock.accept()  # * Blocking
                request_msg = sock.recv(4096)
                method = http_method(request_msg)
                request_msg = parse.unquote(request_msg)
                if not request_verification(request_msg):
                    sock.close()
                    del sock
                    continue
                if method == "GET":
                    print(
                        f"\n 80번 포트로 들어온 HTTP 요청 메세지[{method}]를 감지했습니다. HTTP응답으로 회신합니다.\n{request_msg}\n"
                    )
                    current_page = template_mapping(request_msg)
                    sock.sendall(current_page)
                    sock.close()
                    del sock
                    print('소켓을 제거하였습니다')
                elif method == "POST":
                    print(
                        f"\n 80번 포트로 들어온 HTTP 요청 메세지[{method}]를 감지했습니다. 정보를 처리합니다.\n{request_msg}\n"
                    )
                    db_query = db_query if (db_query := read_db('forum')) else {}
                    with self.lock:
                        try:
                            input_query = extract_query(request_msg)
                            if isinstance(input_query,str):
                                # 여기서 input_quert는 글을 삭제하기 위한 암호다
                                try:
                                    deleted = db_query.pop(input_query)
                                except KeyError:
                                    add_js = """
                                    alert(`암호에 해당하는 글이 없습니다.

글을 작성하실때 암호를 입력하지 않았을 경우
메일 등으로 연락 주시면 삭제해 드리겠습니다.`)
                                    """
                                    self.apply_data(db_query,sock,add_js)
                                else:
                                    self.apply_data(db_query,sock)
                                    print(f'[POST] 글이 삭제되었습니다.\n삭제된 글: {deleted}')
                                sock.close()
                                continue
                            for text,date_time in db_query.values():
                                if text == input_query['text']:
                                    sock.sendall(template_engine(TEMPLATE_MAPPING['/forum']))
                                    raise ValueError
                        except ValueError:
                            self.ignore_to_forum(sock)
                            continue
                        except KeyError:
                            self.ignore_to_forum(sock)
                            continue
                        else:
                            password = input_query['password']
                            text = input_query['text']
                            print(f'[POST]글 등록:{text} \n글 암호: {password}')
                            now = f"{time.strftime('%Y년 %m월 %d일 %X')}"
                            db_query[password] = (text,now)
                            self.apply_data(db_query,sock)
                            sock.close()
                            del sock
                            continue

