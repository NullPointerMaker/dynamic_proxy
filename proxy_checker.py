import logging
import re
from threading import Timer
from typing import Optional

import peewee
import requests
from requests import RequestException

import config
from proxy_filter import Proxy, is_valid, delete_proxy

checked_proxy = 'socks5://127.0.0.1:9050'


def get_checked_proxy():
    return checked_proxy


def set_checked_proxy(cp):
    global checked_proxy
    if cp.type == 'https':
        checked_proxy = 'http://' + cp.address
    else:
        checked_proxy = cp.type + '://' + cp.address


def get_local_ip() -> str:
    r = requests.get('https://httpbin.org/ip')
    return r.json()['origin']


local_ip = get_local_ip()


def check_access(proxies: dict) -> bool:
    logging.info(check_access.__name__)
    try:
        for url in config.check_access:
            r = requests.head(url, proxies=proxies, timeout=config.timeout)
            if r.status_code < 200:
                return False
    except RequestException:  # bad proxy
        return False
    return True


def check_ssl(proxies: dict) -> bool:
    logging.info(check_ssl.__name__)
    if 'http' in config.proxy_type:  # accept plain
        return True
    try:
        r = requests.head('https://httpbin.org', proxies=proxies, timeout=config.timeout)
        return r.status_code > 0
    except RequestException:  # bad proxy
        return False


def check_anonymity(proxies: dict) -> bool:
    logging.info(check_anonymity.__name__)
    if 'transparent' in config.proxy_anonymity:  # accept transparent
        return True
    try:
        r = requests.get('http://httpbin.org/anything', proxies=proxies, timeout=config.timeout)
        if 'anonymous' in config.proxy_anonymity:  # accept anonymous
            anonymous = local_ip not in r.text
            logging.debug('anonymous: ' + str(anonymous))
            return anonymous
        if 'elite' in config.proxy_anonymity:  # accept elite
            headers = r.json()['headers']
            elite = 'Via' not in headers and 'X-Forwarded-For' not in headers  # todo valid?
            logging.debug('elite: ' + str(elite))
            return elite
    except RequestException:  # bad proxy
        return False


def check_country(proxies: dict) -> bool:
    logging.info(check_country.__name__)
    if not config.proxy_country and not config.proxy_country_exclude:  # accept all countries
        return True
    try:
        r = requests.get('http://api.cloudflare.com/cdn-cgi/trace', proxies=proxies, timeout=config.timeout)
        locs = re.findall(r'^loc=([A-Z0-9]{2})$', r.text, re.MULTILINE)
        if locs:
            country = locs[0]
        else:
            logging.error(r.text)
            return False
    except RequestException:  # bad proxy
        return False
    if config.proxy_country and country not in config.proxy_country:
        return False
    if config.proxy_country_exclude and country in config.proxy_country_exclude:
        return False
    return True


def access_weixin(proxies: dict) -> bool:
    logging.info(access_weixin.__name__)
    try:
        r = requests.get('http://mp.weixin.qq.com', proxies=proxies, timeout=config.timeout)
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
        logging.warning('%s: %s access weixin failed' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    logging.info('%s: %s valid' % (check_proxy.__name__, random_proxy.address))
    return random_proxy


def rotate_proxy():
    cp = None
    while not cp:
        cp = check_proxy()
    set_checked_proxy(cp)
    Timer(config.rotate_interval, rotate_proxy).start()
