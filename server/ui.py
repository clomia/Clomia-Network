import os, pickle
from executor import Excutor

PATH = os.path.dirname(os.path.realpath(__file__))

settings = {
    'env_setting':{
        'port_list':[50000,50001,50002,50003,50004,50005,50006,50007,50008,50009,50010,50011,50012,50013]
        },
    'server_setting':{
        (50000,500001):['첫번째 서버',"192.168.219.101","이것은 암호입니다"],
        (500002,500003):['두번째 서버',"192.168.219.101","이것은 암호입니다"],
        (500004,500005):['세번째 서버',"192.168.219.101","이것은 암호입니다"],
    }
}


def set_dir(path) -> str:
    lst = os.listdir(path)
    setting_dir = f'{path}/setting'
    if not 'setting' in lst:
        os.mkdir(setting_dir)
    return setting_dir

setting_dir = set_dir(PATH)
setting_name = "첫 설정"

def write_setting(setting_dir,setting_name,settings):
    with open(f'{setting_dir}/{setting_name}.clomia-setting','wb') as file:
        pickle.dump(settings,file)

def read_setting(setting_dir,setting_name) -> dict:
    with open(f'{setting_dir}/{setting_name}.clomia-setting','rb') as file:
        settings = pickle.load(file)
        return settings
setting = read_setting(setting_dir,"첫 설정")
print(setting)


def terminal_io() -> dict:
    setting_dir =  set_dir(PATH)
    setting_iter = map(lambda x:x[:-15],os.listdir(setting_dir))
    if tuple(setting_iter):
        for setting in setting_iter:
            print(setting)
        setting_name = input("등록된 설정은 위와 같습니다. 원하시는 설정명을 입력해주세요. 새롭게 설정하시려면 엔터를 눌러주세요.\n>>> ")
        if setting_name:
            return read_setting(PATH,setting_name)
    print("""
    서버 설정을 시작합니다. 사용하는 인터넷에 포트 포워딩이 된 상태여야 합니다 (권장: 40000 ~ 49151 사이의 포트)\n
    사용 가능한 포트번호들을 입력해주세요. DMZ(모든 포트)를 오픈한 경우 엔터를 눌러주세요.
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
        #! ports_list가 완성된다 이것을 사용하라


    msg_1 = ""
    input


'''
#? 6코어 CPU 윈도우 환경에서 대략 2000개 까지는 문제없이 실행 가능했다
for i in range(0,2000,2):
    ports = (i+40000,i+40001)
    command = [f'{i+1}번째 서버',"192.168.219.101","이것은 암호입니다"]
    setting[ports] = command


#Excutor(setting).run()

'''


#python server_constructor.py 50000 50001 안녕 192.168.219.101 이것은암호입니다
#? 사용자입력 : 사용 가능한 포트 리스트(DMZ포트포워딩인지도 확인) -> 오픈 가능한 서버 갯수 반환 -> for돌면서 서버명과 암호를 입력받기 ->
#? 한번 설정한거는 피클링해서 저장하자 (암호,포트리스트는 노출되면 안되니까)