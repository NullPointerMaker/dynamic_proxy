import logging
from datetime import datetime as Datetime

import requests
from bs4 import BeautifulSoup

import config
from proxy_filter import Proxy, filter_proxy


def scrape_free_proxy_list_net(url: str):  # free-proxy-list.net
    # include:
    # sslproxies.org
    # us-proxy.org
    logging.info('%s starting' % url)
    if 'https' not in config.proxy_type and 'http' not in config.proxy_type:
        return
    r = requests.get(url)
    if 200 != r.status_code:
        logging.warning('%s: HTTP %d' % (scrape_free_proxy_list_net.__name__, r.status_code))
        return
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', attrs={'id': 'proxylisttable'})
    rows = table.find_all("tr")
    logging.info('%s %d proxies' % (url, len(rows) - 1))
    for row in rows:
        cells = row.find_all("td")
        if len(cells) == 8:
            address = cells[0].text
            address += ':' + cells[1].text
            proxy = Proxy()
            proxy.address = address.strip('&nbsp;')
            proxy.type = 'https' if 'yes' in cells[6].text.lower() else 'http'
            proxy.anonymity = cells[4].text.lower().strip('&nbsp;').rstrip(' proxy')
            proxy.country = cells[2].text.upper().strip('&nbsp;')
            filter_proxy(proxy)
    logging.info('%s ending' % url)


def is_updated(timestamp: Datetime) -> bool:
    now = Datetime.now()
    return (now - timestamp).total_seconds() < 3600


def is_updated_github(url: str) -> bool:
    url = url.replace('://github.com/', '://api.github.com/repos/')
    url = url.replace('/raw/HEAD/', '/commits?page=1&per_page=1&path=')
    try:
        r = requests.get(url)
        if 200 != r.status_code:
            logging.warning('%s: HTTP %d' % (is_updated_github.__name__, r.status_code))
            return False
        commits = r.json()
        date = commits[0]['commit']['author']['date']
        timestamp = Datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    except (IOError, KeyError, ValueError, TypeError, AttributeError) as e:
        logging.exception(e)
        return False
    return is_updated(timestamp)


def get_type_anonymity_set() -> set:
    settings = set()
    for proxy_type in config.proxy_type:
        if 'socks' in proxy_type:
            settings.add((proxy_type, ''))
        else:
            for anonymity in config.proxy_anonymity:
                settings.add((proxy_type, anonymity))
    return settings


type_anonymity_set = get_type_anonymity_set()


def get_type_anonymity_country_set() -> set:
    settings = set()
    for paras in type_anonymity_set:
        if not config.proxy_country:
            settings.add((paras[0], paras[1], ''))
        for country in config.proxy_country:
            settings.add((paras[0], paras[1], country))
    return settings


type_anonymity_country_set = get_type_anonymity_country_set()
