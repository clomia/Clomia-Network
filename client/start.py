import os, re, pickle, time

ipv4_pattern = re.compile(
    "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
PATH: str = os.path.dirname(os.path.realpath("start"))


def set_dir(path) -> str:
    """
    설정 디렉토리를 반환한다.
    이때 설정 디렉토리가 없다면 생성 후 반환한다.
    """
    lst = os.listdir(path)
    setting_dir = f"{path}/setting"
    if not "setting" in lst:
        os.mkdir(setting_dir)
    return setting_dir


def clear_socket(sock):
    sock.close()
    del sock


def port_verification(port: str) -> int:
    if not port:
        print("공백을 입력하셨습니다.")
        return False
    try:
        port = int(port)
    except ValueError:
        print("포트번호는 숫자입니다. 숫자를 입력해주세요.")
        return False
    if 1024 > port or 65535 < port:
        print("사용 가능한 포트번호는 1024 ~ 65535 사이입니다")
        return False
    return port


def setting(recursive=False) -> tuple:
    """
    정보를 수집한뒤 설정을 저장하고 \n
    (서버ip,서버 입력포트,서버 응답포트,암호) 를 반환한다.
    """
    hello = "안녕하세요 clomia입니다.\n" if not recursive else ""
    info_msg = (
        "-" * 40
        + "\n"
        + hello
        + "타겟 서버와의 연결을 구축하기에 앞서서 아래의 정보를 알고 계셔야 합니다.\n\n"
        + "[1] 서버의 IP (외부ip)\n"
        + "[2] 서버의 입력용 포트번호\n"
        + "[3] 서버의 응답용 포트번호\n"
        + "[4] (기밀정보) 서버의 암호\n\n"
        + "위 정보들은 서버 관리자가 서버 소프트웨어로 서버를 오픈할 때 안내됩니다.\n"
        + "접속을 위하여 서버 관리자에게 위의 정보들을 제공받으셔야 합니다.\n"
        + "모두 확인하셨다면 엔터를 눌러주세요...\n"
        + "-" * 40
        + "\n"
    )
    input(info_msg)
    server_ip = input("[1/4]접속할 서버의 IP를 입력해주세요. (IPv4 ,External ip)\n>>>")
    while not ipv4_pattern.match(server_ip):
        print(
            "올바른 ip를 입력해주세요. 우리는 IPv4 프로토콜을 사용합니다.\n" + "참고 https://ko.wikipedia.org/wiki/IPv4 \n"
        )
        input("(엔터 누르기)>>>")
        print("\n" * 100)
        setting(recursive=True)
        break
    while True:
        port = port_verification(input("[2/4]서버의 입력용 포트번호를 입력해주세요\n>>>"))
        if not port:
            continue
        server_input_port = port
        break
    while True:
        port = port_verification(input("[3/4]서버의 응답용 포트번호를 입력해주세요\n>>>"))
        if not port:
            continue
        if server_input_port == port:
            print("위에서 입력한 입력용 포트번호와 같습니다. 다른 번호를 입력해 주세요.")
            continue
        server_response_port = port
        break
    while True:
        secret_code = input("[4/4]서버의 암호를 입력해주세요.\n>>>")
        if not secret_code:
            print("공백을 입력하셨습니다.")
        else:
            break
    msg = (
        "-" * 40
        + "\n"
        + f"서버의 IP: {server_ip}\n"
        + f"서버의 입력용 포트번호: {server_input_port}\n"
        + f"서버의 응답용 포트번호: {server_response_port}\n\n"
        + f"(기밀정보) 서버의 암호: {secret_code}\n"
        + "-" * 40
        + "\n"
        + "위의 정보가 맞다면 엔터를 눌러주세요.\n"
        + "다시 설정하시려면 n을 입력해주세요\n"
        + ">>>"
    )
    if input(msg):
        print("\n" * 100)
        setting(recursive=True)
    msg = (
        '설정을 저장합니다. 설정명을 입력해주세요.   (설정명 예시: clomia서버)"\n'
        + "(설정을 저장하지 않고 진행하시려면 엔터를 눌러주세요)\n"
        + ">>>"
    )
    settings = (server_ip, server_input_port, server_response_port, secret_code)
    setting_name = input(msg)
    if setting_name:
        setting_dir = set_dir(PATH)
        with open(f"{setting_dir}/{setting_name}.clomia-setting", "wb") as file:
            pickle.dump(settings, file)
        print(f"설정 {setting_name}을(를) 저장하였습니다.")
    return settings


def check_settings() -> list:
    """ 저장된 세팅파일이 있는지 확인하고 있다면 세팅 리스트를 반환한다."""
    if setting_list := os.listdir(set_dir(PATH)):
        return setting_list


def reset_settings():
    """ 저장된 세팅파일을 모두 삭제한다 """
    setting_dir = set_dir(PATH)
    for setting in os.listdir(setting_dir):
        os.remove(f"{setting_dir}/{setting}")


def terminal_io():
    """
    사용자와 대화하면서 설정한다\n
    최종적으로(서버ip,서버 입력포트,서버 응답포트,암호) 를 반환한다
    """
    if setting_list := check_settings():
        print("저장된 설정이 있습니다.\n" + "-" * 40 + "\n")
        setting_list = list(map(lambda x: x[:-15], setting_list))
        for setting_name in setting_list:
            print(setting_name)
        print("\n" + "-" * 40 + "\n")
        msg = (
            "저장된 설정은 위와 같습니다. 원하는 설정명을 입력해주세요. 새롭게 설정하시려면 엔터를 눌러주세요.\n"
            + "  등록된 설정을 모두 지우고 새롭게 설정하시려면 'clear'를 입력해주세요.\n\n"
            + ">>>"
        )
        setting_name = input(msg)
        if setting_name and (setting_name != "clear"):
            if not (setting_name in setting_list):
                print("이 설정은 존재하지 않습니다.")
                terminal_io()
            setting_dir = set_dir(PATH)
            with open(f"{setting_dir}/{setting_name}.clomia-setting", "rb") as file:
                server_ip, server_input_port, server_response_port, secret_code = pickle.load(file)
            msg = (
                "-" * 40
                + "\n"
                + f"설정({setting_name})을(를) 성공적으로 읽어들였습니다.\n"
                + f"서버 IP: {server_ip}\n"
                + f"서버 입력 포트: {server_input_port}\n"
                + f"서버 응답 포트: {server_response_port}\n"
                + f"(기밀 정보)암호: {secret_code}\n"
                + "-" * 40
                + "\n"
                + "위 정보가 맞다면 엔터를 눌러주세요. 다시 시작하시려면 'n'을 입력해주세요\n>>>"
            )
            if input(msg):
                terminal_io()
            return (server_ip, server_input_port, server_response_port, secret_code)
        else:
            reset_settings()
            terminal_io()
    else:
        print("설정을 시작합니다...")
        time.sleep(0.5)
        return setting()


def clomia_network_info() -> tuple:
    """ clomia Network 공식 서버 정보를 반환 한다 """
    __server_ip = "192.168.219.102"
    __server_input_port = 45000
    __server_response_port = 45001
    __secret_code = "9LK2Dx6j5SjXfeju8x7r"
    return (__server_ip, __server_input_port, __server_response_port, __secret_code)



def get_setting():
    msg = (
        "\n-------------------Clomia Network가 운영하는 공식 서버로 접속합니다.-------------------\n\n"
        + "이대로 진행하려면 엔터를 눌러주세요. (사설 서버로 접속하려면 'y' 를 입력해주세요.)\n\n"
        + ">>>"
    )
    if input(msg):
        return terminal_io()
    else:
        return clomia_network_info()


#! transmission에 정보전달 -> transmission이 인스팩트 코드 수신 후 receiving 에게 전달,실행 - 끝!
if __name__ == "__main__":
    server_ip, server_input_port, server_response_port, secret_code = get_setting()
    os.system(
        f"start cmd /k {PATH}/communication/transmission.py {server_ip} {server_input_port} {server_response_port} {secret_code}"
    )
