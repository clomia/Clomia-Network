from typing import Dict,Tuple,List,Union
from server_constructor import Server
server_set = Dict[Tuple[int,int],List[Union[str,bytes]]]
server_ele = Tuple[Server,Tuple[str,str]]

class Excutor:
    """ 다수의 서버객체를 실행시켜준다. """
    def __init__(self,servers:server_set):
        """ {(입력포트,응답포트):[이름,ip,암호:bytes], ...}딕셔너리 를 받아서 실행한다 """
        self.server_list:List[server_ele] = []
        for ports,property in servers.items():
            self.server_list.append((Server(*property),ports))
        self.server_count = len(self.server_list)
        Excutor.servers_open(self.server_list)


    @staticmethod
    def servers_open(server_eles:List[server_set]): #Excutor.server_open(self.server_list->ele)
        for setting_ele in server_eles:
            server_obj,ports = setting_ele
            server_obj.open(*ports)
setting = {
    (50000,50001):['실험용',"192.168.219.101","이것은 암호입니다".encode("utf-8")],
    (50002,50003):['2222',"192.168.219.101","이것은 암호입니다".encode("utf-8")]
    }

Excutor(setting)