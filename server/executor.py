import os,subprocess
from itertools import cycle
from typing import Dict,Tuple,List,Union
server_set = Dict[Tuple[int,int],List[Union[str,bytes]]]

class Excutor:
    """ 다수의 서버객체를 실행시켜준다. 멀티 프로세싱과 쓰레드 분배로 CPU 코어들을 최대한 사용한다"""
    def __init__(self,servers:server_set):
        """ {(입력포트,응답포트):[이름,ip,암호:str], ...}딕셔너리 를 받아서 세팅한다 """
        self.server_eles = servers
        self.server_settings = [] # ['입력포트', '응답포트', '서버이름' ,'ip' ,'암호']
        for ports,property in servers.items():
            self.server_settings.append([str(ports[0]),str(ports[1])]+property)
        self.server_count = len(self.server_settings)
        self.cpu_count = os.cpu_count()
        self.path = os.path.dirname(os.path.realpath(__file__))
    
    def run(self):
        """ 균등하게 작업단위를 생성한 뒤 필요한 만큼(최대=머신의 CPU갯수) 프로세스를 생성하여 병렬 실행합니다 """
        print(f"오픈할 서버 갯수는 {self.server_count}개이며 이 컴퓨터의 CPU 갯수는 {self.cpu_count}개 입니다. 작업 배분을 시작합니다...")
        process_frame = {}
        cpu_counter = range(1,self.cpu_count)
        for count in cpu_counter:
            process_frame[count] = []
        for number,server_setting in zip(cycle(cpu_counter),self.server_settings):
            process_frame[number].append(server_setting)
        print(f'현재 사용중인 CPU를 제외한 {self.cpu_count-1}개의 CPU에 할당할 작업 배분 계획을 수립하였습니다.\n\n할당 표: {process_frame}\n\n멀티 프로세스를 구성합니다...')
        process_list = []
        for setting_set in process_frame.values():
            if not setting_set:
                break
            command = ['python',f'{self.path}/server_constructor.py']
            for setting in setting_set:
                command.extend(setting)
            print(f'커멘드를 생성하였습니다\n커맨드 : {command}\n프로세스를 생성합니다')
            process_list.append(subprocess.Popen(command))
        print(f'모든 프로세스가 성공적으로 생성되었습니다.\n프로세스 리스트:{process_list}\nCPU {len(process_list)}개를 사용하여 실행합니다...')
        for process in process_list:
            process.communicate()

    @staticmethod
    def servers_open(server_eles:List[server_set]):
        """ {(입력포트,응답포트):[이름,ip,암호:bytes], ...}딕셔너리 를 받아서 실행합니다 순수하게 직렬 실행합니다 """
        for setting_ele in server_eles:
            server_obj,ports = setting_ele
            server_obj.open(*ports)


