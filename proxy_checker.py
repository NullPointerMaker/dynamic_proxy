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


def get_local_ip() -> str:
    r = requests.get('https://httpbin.org/ip')
    return r.json()['origin']


local_ip = get_local_ip()


def check_access(proxies: dict) -> bool:
    try:
        for url in config.check_access:
            logging.info('%s: %s to %s' % (check_access.__name__, proxies['http'], url))
            r = requests.head(url, proxies=proxies, timeout=config.timeout)
            if r.status_code < 200:
                return False
    except RequestException:  # bad proxy
        return False
    return True


def check_ssl(proxies: dict) -> bool:
    if 'http' in config.proxy_type:  # accept plain
        return True
    logging.info('%s: %s' % (check_ssl.__name__, proxies['http']))
    try:
        r = requests.head('https://httpbin.org', proxies=proxies, timeout=config.timeout)
        return r.status_code > 0
    except RequestException:  # bad proxy
        return False


def check_anonymity(proxies: dict) -> bool:
    if 'transparent' in config.proxy_anonymity:  # accept transparent
        return True
    logging.info('%s: %s' % (check_anonymity.__name__, proxies['http']))
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
    if not config.proxy_country and not config.proxy_country_exclude:  # accept all countries
        return True
    logging.info('%s: %s' % (check_country.__name__, proxies['http']))
    try:
        r = requests.get('http://api.cloudflare.com/cdn-cgi/trace', proxies=proxies, timeout=config.timeout)
        locs = re.findall(r'^loc=([A-Z0-9]{2})$', r.text, re.MULTILINE)
        if locs:
            country = locs[0]
        else:
            logging.error('%s: %s by cloudflare failed' % (check_country.__name__, proxies['http']))
            logging.debug(r.text)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:60.0) Gecko/20100101 Firefox/60.0'}
            r = requests.get('http://www.whatismyip.com.tw', proxies=proxies, headers=headers, timeout=config.timeout)
            countries = re.findall(r'country="([A-Z0-9]{2})"', r.text, re.MULTILINE)
            if countries:
                country = countries[0]
            else:
                logging.error('%s: %s by whatismyip failed' % (check_country.__name__, proxies['http']))
                logging.debug(r.text)
                return False
    except RequestException:  # bad proxy
        return False
    if config.proxy_country and country not in config.proxy_country:
        return False
    if config.proxy_country_exclude and country in config.proxy_country_exclude:
        return False
    return True


def check_content(proxies: dict) -> bool:
    try:
        for url in config.check_content:
            logging.info('%s: %s from %s' % (check_content.__name__, proxies['http'], url))
            r = requests.get(url, proxies=proxies, timeout=config.timeout)
            if r.status_code != 200:  # api offline
                return False
            if config.check_content[url] not in r.text:
                logging.debug(r.text)
                return False
    except RequestException:  # bad proxy
        return False


def check_proxy() -> Optional[str]:
    random_proxy: Proxy = Proxy.select().order_by(peewee.fn.Random()).get()
    logging.info('%s: %s' % (check_proxy.__name__, random_proxy.address))
    if not is_valid(random_proxy):
        logging.warning('%s: %s invalid' % (check_proxy.__name__, random_proxy.address))
        delete_proxy(random_proxy)
        return None
    if 'https' == random_proxy.type:
        random_proxy.type = 'http'
    proxies = {'http': random_proxy.type + '://' + random_proxy.address}
    proxies['https'] = proxies['http']
    if not check_access(proxies):
        logging.warning('%s: %s invalid access' % (check_proxy.__name__, proxies['http']))
        delete_proxy(random_proxy)
        return None
    if not check_ssl(proxies):
        logging.warning('%s: %s invalid ssl' % (check_proxy.__name__, proxies['http']))
        delete_proxy(random_proxy)
        return None
    if not check_anonymity(proxies):
        logging.warning('%s: %s invalid anonymity' % (check_proxy.__name__, proxies['http']))
        delete_proxy(random_proxy)
        return None
    if not check_country(proxies):
        logging.warning('%s: %s invalid country' % (check_proxy.__name__, proxies['http']))
        delete_proxy(random_proxy)
        return None
    if not check_content(proxies):
        logging.warning('%s: %s invalid content' % (check_proxy.__name__, proxies['http']))
        delete_proxy(random_proxy)
        return None
    logging.info('%s: %s valid' % (check_proxy.__name__, proxies['http']))
    return proxies['http']


def rotate_proxy():
    cp = None
    while not cp:
        cp = check_proxy()
    global checked_proxy
    checked_proxy = cp
    Timer(config.rotate_interval, rotate_proxy).start()
