import time
import requests
from src.projecthope.common.variables import headers

from stem import Signal
from stem.control import Controller


def get_tor_session():
    tor_session = requests.session()
    tor_session.proxies = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}

    return tor_session


def change_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password='myfirsttorproject')
        controller.signal(Signal.NEWNYM)
        controller.close()


for i in range(10):
    session = get_tor_session().get("http://httpbin.org/ip", headers=headers).text
    change_ip()

    print(session)
    time.sleep(1)
