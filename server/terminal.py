import os, pickle,socket, requests
from executor import Excutor
from http_manager import HttpServe


PATH = os.path.dirname(os.path.realpath('terminal'))

def get_external_ip():
    """ 네이버 서버를 이용한다 """
    response = requests.get("https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=%EB%82%B4ip")
    return response.text.split('class="ip_chk_box">')[1].split("</div>")[0]

def set_dir(path) -> str:
    lst = os.listdir(path)
    setting_dir = f'{path}/setting'
    if not 'setting' in lst:
        os.mkdir(setting_dir)
    return setting_dir


def write_setting(setting_dir,setting_name,settings):
    with open(f'{setting_dir}/{setting_name}.clomia-setting','wb') as file:
        pickle.dump(settings,file)

def read_setting(setting_dir,setting_name) -> dict:
    try:
        with open(f'{setting_dir}/{setting_name}.clomia-setting','rb') as file:
            settings = pickle.load(file)
    except FileNotFoundError:
        print('설정이 존재하지 않습니다')
        raise
    key_list = list(settings.keys())
    key = key_list[0]
    ip = settings[key][1]
    internal_ip = socket.gethostbyname(socket.gethostname())
    if ip != internal_ip:
        msg = ("ip검사 대조 결과 설정에 작성되있는 ip가 현재 내부 ip와 다릅니다.\n"
            +f"현재 내부 ip: {internal_ip} , 설정 파일에 작성된 ip: {ip}"
            +"정상적인 실행을 위해서 설정 파일을 현재 ip로 갱신한뒤 실행합니다.\n"
            +"동의하시면 엔터를 눌러주세요.\n\n")
        if not input(msg):
            for key in key_list:
                settings[key][1] = internal_ip
            write_setting(set_dir(PATH),setting_name,settings)
            read_setting(setting_dir,setting_name)
    return settings



def make_settings_io() -> dict:
    internal_ip = socket.gethostbyname(socket.gethostname())
    setting_dir = set_dir(PATH)
    setting_tuple = tuple(map(lambda x:x[:-15],os.listdir(setting_dir)))
    if setting_tuple:
        print('-'*50)
        for setting in setting_tuple:
            print(f'설정명:{setting}')
        print('-'*50)
        msg = ("등록된 설정은 위와 같습니다. 원하는 설정명을 입력해주세요. 새롭게 설정하시려면 엔터를 눌러주세요.\n"
            +"  등록된 설정을 모두 지우고 새롭게 설정하시려면 'clear'를 입력해주세요.\n"
            +">>>")
        setting_name = input(msg)
        if setting_name and setting_name != "clear":
            return read_setting(setting_dir,setting_name),internal_ip
        elif setting_name == 'clear':
            for setting in os.listdir(setting_dir):
                os.remove(f'{setting_dir}/{setting}')
            print("모든 설정들이 삭제되었습니다.")
    print("""
    서버 설정을 시작합니다. 사용하는 인터넷에 포트 포워딩이 된 상태여야 합니다 (권장: 40000 ~ 49151 사이의 포트)

    [주요 메세지!] -> 80번(HTTP) 포트를 제외하고 사용 가능한 포트번호들을 입력해주세요. 
    
    DMZ(모든 포트)를 오픈한 경우 엔터를 눌러주세요.
        참고: 외부포트가 내부포트와 동일한 번호로 1:1 대응된다는 가정 하에 설정합니다.\n
    입력 종료는 엔터키 입니다.
        """)
    count = 0
    ports_list = []
    port_pair = []
    all_ports = []
    while port:= input('>>> '):
        port = int(port)
        if port in all_ports:
            print(f'{port}는 이미 입력된 포트번호입니다. 다른 포트번호를 입력해주세요.\n입력된 포트들: {all_ports}')
            continue
        if port in tuple(range(1,1025)):
            print('1024 미만의 포트는 예약된 포트번호입니다 다른 포트번호를 입력해주세요')
            continue
        if port > 65535:
            print('포트는 65535번까지 있습니다. 65535보다 작은 숫자를 입력해주세요')
            continue
        count += 1
        all_ports.append(port)
        if count % 2 == 0:
            port_pair.append(port)
            ports = tuple(port_pair)
            ports_list.append(ports)
            port_pair.clear()
        else:
            port_pair.append(port)
    if not count:
        while True:
            msg = ('몇 개의 서버를 오픈할지 숫자로 입력해 주세요. 포트번호를 자동 세팅합니다.\n\n'
                +'참고 :  인텔® 코어™ i5-9400F 프로세서(6코어)로 윈도우 10에서 돌렸을때 서버가 대략 2000개 까지 안정적으로 오픈되는걸 확인했습니다.\n'
                +'서버 수가 2000개를 상회하는 경우 CPU 코어들에게 전달하는 명령어 길이가 길어짐으로 인해서 문제가 발생하는것을 확인했습니다. \n'
                +'즉, 코어 수가 가장 중요합니다.\n'
                +'>>>')
            server_count = input(msg)
            try:
                server_count = int(server_count)
                break
            except ValueError:
                print('\n\n\n\n-------------숫자를 입력해 주세요.-------------\n\n')
                continue
        all_ports_list = list(range(40000,40000+int(server_count)*2))
        ports_list = []
        port_pair = []
        for port in all_ports_list:
            if len(port_pair) == 1:
                port_pair.append(port)
                ports = tuple(port_pair)
                ports_list.append(ports)
                port_pair.clear()
            else:
                port_pair.append(port)
    msg = (f"{len(ports_list)}개의 서버를 열 수 있습니다.\n"
            +"몇 개의 서버를 오픈할지 숫자로 입력해 주세요.\n"
            +"모두 오픈은 엔터를 눌러주세요.\n"
            +">>>")
    server_count = 0
    while value := input(msg):
        try:
            server_count = int(value)
            if server_count > (useable := len(ports_list)):
                print(f'{useable}개 이하의 서버를 열 수 있습니다.')
                continue
            else:
                break
        except TypeError:
            print('\n숫자를 입력해주세요\n\n')
            continue
    if not server_count:
        server_count = len(ports_list)
    print("이제 기기의 정보를 수집합니다...")

    host_name = socket.gethostname()
    external_ip = get_external_ip()
    print(f"""
    Host Name: {host_name} , 내부 IP: {internal_ip} , 외부 IP: {external_ip}\n
        참고: 클라이언트 측에서 접근할때는 "외부 IP:포트번호" 를 사용해야 합니다. 
        브라우저로 접속하면 Clomia Network 웹 서버로써 HTTP통신 규약대로 응답 합니다.
    """)
    settings = {}
    for count,port_pair in zip(range(1,server_count+1),ports_list):
        print(f'{count}번째 서버를 입력포트: {port_pair[0]},응답포트: {port_pair[1]} 로 설정합니다.')
        while not (server_name := input("서버의 이름을 정해주세요.\n>>>")):
            print('공백은 입력받지 않습니다.')
        while (not (secret_code := input("서버의 암호를 정해주세요.(공백이 없어야 합니다.)\n>>>"))) or (' ' in secret_code):
            print('공백은 입력받지 않습니다.')
        settings[port_pair] = [server_name,internal_ip,secret_code]
    msg = ("설정이 완료되었습니다. 설정을 저장합니다. 이 설정의 이름을 입력해주세요.\n"
            +"저장하지 않고 진행하시려면 엔터를 눌러주세요.\n"
            +">>>")
    setting_name = input(msg)
    if setting_name:
        write_setting(setting_dir,setting_name,settings)
        print('설정파일을 생성,저장하였습니다.')
    return settings,internal_ip
        

def run_web_server_io(internal_ip):
    if not input('80번 포트가 열려있지 않다면 "n"을 입력해주세요.\n80번 포트가 열려있다면 엔터를 눌러주세요 웹 서비스를 시작합니다...\n>>>'):
        HttpServe(internal_ip).start()
        print('[80번 포트...]웹 서비스를 실행하였습니다')


def main():
    while True:
        try:
            settings,internal_ip = make_settings_io()
            break
        except FileNotFoundError:
            continue
    run_web_server_io(internal_ip)
    Excutor(settings).run()

if __name__ == "__main__":
    main()
