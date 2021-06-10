from threading import Timer
from typing import Optional

import requests
import socks
from peewee import fn
from requests import RequestException

import config
from proxy_filter import Proxy, is_valid, delete_proxy

checked_proxy = dict()


def get_checked_proxy() -> dict:
    return checked_proxy


def set_checked_proxy(**kwargs):
    global checked_proxy
    checked_proxy = kwargs


def get_local_ip() -> str:
    r = requests.get('https://httpbin.org/ip')
    return r.json()['origin']


local_ip = get_local_ip()


def check_access(proxies: dict) -> bool:
    try:
        r = requests.options('http://twitter.com', proxies=proxies)
        return r.status_code > 0
    except RequestException:  # bad proxy
        return False


def check_ssl(proxies: dict) -> bool:
    if 'http' in config.proxy_type:  # accept plain
        return True
    try:
        r = requests.options('https://httpbin.org/status/233', proxies=proxies)
        return r.status_code == 233
    except RequestException:  # bad proxy
        return False


def check_anonymity(proxies: dict) -> bool:
    if 'transparent' in config.proxy_anonymity:  # accept transparent
        return True
    try:
        r = requests.get('http://httpbin.org/ip', proxies=proxies)
        if 'anonymous' in config.proxy_anonymity:  # accept anonymous
            return local_ip not in r.text
        r = requests.get('http://httpbin.org/headers', proxies=proxies)
        if 'elite' in config.proxy_anonymity:  # accept elite
            headers = r.json()['headers']
            return 'Via' not in headers and 'X-Forwarded-For' not in headers  # todo valid?
    except RequestException:  # bad proxy
        return False


def check_country(proxies: dict) -> bool:
    if not config.proxy_country and not config.proxy_country_exclude:  # accept all countries
        return True
    try:
        r = requests.get('https://echo.copythat.workers.dev', proxies=proxies)
        country = r.json()['cf']['country']
    except RequestException:  # bad proxy
        return False
    if config.proxy_country and country not in config.proxy_country:
        return False
    if config.proxy_country_exclude and country in config.proxy_country_exclude:
        return False
    return True


def access_weixin(proxies: dict) -> bool:
    try:
        r = requests.get('http://mp.weixin.qq.com', proxies=proxies)
        if r.status_code != 200:  # api offline
            return False
        return 'Chrome' in r.text
    except RequestException:  # bad proxy
        return False


def check_proxy() -> Optional[Proxy]:
    random_proxy: Proxy = Proxy.select().order_by(fn.Random())
    if not is_valid(random_proxy):
        delete_proxy(random_proxy)
        return None
    proxies = {}
    if 'http' in random_proxy.type:
        proxies['http'] = 'http://' + random_proxy.address
    elif 'socks' in random_proxy.type:
        proxies['http'] = random_proxy.type + '://' + random_proxy.address
    proxies['https'] = proxies['http']
    if not check_access(proxies):
        delete_proxy(random_proxy)
        return None
    if not check_ssl(proxies):
        delete_proxy(random_proxy)
        return None
    if not check_anonymity(proxies):
        delete_proxy(random_proxy)
        return None
    if not check_country(proxies):
        delete_proxy(random_proxy)
        return None
    if not access_weixin(proxies):
        delete_proxy(random_proxy)
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
    addr = str(cp.address).split(':', 1)[0]
    port = int(addr[1])
    set_checked_proxy(type=proxy_type, host=addr, port=port)
    Timer(config.rotate_interval, rotate_proxy).start()
