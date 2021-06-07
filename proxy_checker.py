from threading import Timer
from typing import Optional

import requests
import socks
from peewee import fn
from requests import RequestException

import config
from proxy_filter import Proxy, is_valid

global checked_proxy


def get_checked_proxy() -> dict:
    return checked_proxy


def set_checked_proxy(**kwargs):
    checked_proxy.update(kwargs)


def get_local_ip() -> str:
    r = requests.get('http://httpbin.org/ip')
    return r.json()['origin']


local_ip = get_local_ip()


def check_anonymity(proxies: dict) -> bool:
    try:
        r = requests.get('http://httpbin.org/ip', proxies=proxies, verify=False)
        if r.status_code != 200:  # api offline
            return False
        anonymous = local_ip not in r.text
    except RequestException:  # bad proxy
        return False
    if not config.proxy_anonymity:  # accept no anonymity
        return True
    if 'transparent' in config.proxy_anonymity:  # accept transparent
        return True
    return anonymous


def check_weixin(proxies: dict) -> bool:
    try:
        r = requests.get('http://mp.weixin.qq.com', proxies=proxies, verify=False)
        if r.status_code != 200:  # api offline
            return False
        return 'Chrome' in r.text
    except RequestException:  # bad proxy
        return False


def check_proxy() -> Optional[Proxy]:
    random_proxy: Proxy = Proxy.select().order_by(fn.Random())
    if not is_valid(random_proxy):
        random_proxy.delete()
        return None
    proxies = {}
    if 'http' in random_proxy.type:
        proxies['http'] = 'http://' + random_proxy.address
    elif 'socks' in random_proxy.type:
        proxies['http'] = random_proxy.type + 'h://' + random_proxy.address
    proxies['https'] = proxies['http']
    if not check_anonymity(proxies):
        random_proxy.delete()
        return None
    if not check_weixin(proxies):
        random_proxy.delete()
        return None
    return random_proxy


def rotate_proxy():
    cp = None
    while not cp:
        cp = check_proxy()

    proxy_type = 0
    if 'http' in cp.type:
        proxy_type = socks.PROXY_TYPE_HTTP
    elif 'socks4' in cp.type:
        proxy_type = socks.PROXY_TYPE_SOCKS4
    elif 'socks5' in cp.type:
        proxy_type = socks.PROXY_TYPE_SOCKS5
    addr = str(cp.address).split(':', 1)
    port = int(addr[1])
    set_checked_proxy(type=proxy_type, host=addr[0], port=port)

    Timer(config.rotate_interval, rotate_proxy).start()
