import logging
from json import JSONDecodeError
from threading import Timer
from typing import Optional

import peewee
import socks
from requests import Session, RequestException
from requests.adapters import HTTPAdapter

import config
from proxy_filter import Proxy, is_valid, delete_proxy

timeout = 60
session = Session()
session.mount('http://', HTTPAdapter(max_retries=5))
session.mount('https://', HTTPAdapter(max_retries=5))

checked_proxy = dict()


def get_checked_proxy() -> dict:
    return checked_proxy


def set_checked_proxy(**kwargs):
    global checked_proxy
    checked_proxy = kwargs


def get_local_ip() -> str:
    r = session.get('https://httpbin.org/ip')
    return r.json()['origin']


local_ip = get_local_ip()


def check_access(proxies: dict) -> bool:
    try:
        r = session.head('http://twitter.com', proxies=proxies)
        return r.status_code > 0
    except RequestException:  # bad proxy
        return False


def check_ssl(proxies: dict) -> bool:
    if 'http' in config.proxy_type:  # accept plain
        return True
    try:
        r = session.head('https://httpbin.org', proxies=proxies)
        return r.status_code > 0
    except RequestException:  # bad proxy
        return False


def check_anonymity(proxies: dict) -> bool:
    if 'transparent' in config.proxy_anonymity:  # accept transparent
        return True
    try:
        r = session.get('http://httpbin.org/ip', proxies=proxies, timeout=timeout)
        if 'anonymous' in config.proxy_anonymity:  # accept anonymous
            return local_ip not in r.text
        r = session.get('http://httpbin.org/headers', proxies=proxies, timeout=timeout)
        if 'elite' in config.proxy_anonymity:  # accept elite
            headers = r.json()['headers']
            return 'Via' not in headers and 'X-Forwarded-For' not in headers  # todo valid?
    except RequestException:  # bad proxy
        return False


def check_country(proxies: dict) -> bool:
    if not config.proxy_country and not config.proxy_country_exclude:  # accept all countries
        return True
    r = None
    try:
        r = session.get('https://echo.copythat.workers.dev', proxies=proxies, timeout=timeout)
        country = r.json()['cf']['country']
    except RequestException as e:  # bad proxy
        logging.debug(e)
        return False
    except JSONDecodeError:
        logging.debug(r.text)
        return False
    if config.proxy_country and country not in config.proxy_country:
        return False
    if config.proxy_country_exclude and country in config.proxy_country_exclude:
        return False
    return True


def access_weixin(proxies: dict) -> bool:
    try:
        r = session.get('https://mp.weixin.qq.com', proxies=proxies, timeout=timeout)
        if r.status_code != 200:  # api offline
            return False
        return 'Chrome' in r.text
    except RequestException:  # bad proxy
        return False


def check_proxy() -> Optional[Proxy]:
    random_proxy: Proxy = Proxy.select().order_by(peewee.fn.Random()).get()
    logging.info('%s: %s' % (check_proxy.__name__, random_proxy.address))
    if not is_valid(random_proxy):
        logging.warning('%s: %s not valid' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    proxies = {}
    if 'http' in random_proxy.type:
        proxies['http'] = 'http://' + random_proxy.address
    elif 'socks' in random_proxy.type:
        proxies['http'] = random_proxy.type + '://' + random_proxy.address
    proxies['https'] = proxies['http']
    if not check_access(proxies):
        logging.warning('%s: %s not access' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    if not check_ssl(proxies):
        logging.warning('%s: %s invalid ssl' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    if not check_anonymity(proxies):
        logging.warning('%s: %s invalid anonymity' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    if not check_country(proxies):
        logging.warning('%s: %s invalid country' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    if not access_weixin(proxies):
        logging.warning('%s: %s not access weixin' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    logging.info('%s: %s valid' % (check_proxy.__name__, random_proxy.address))
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
