import json
import logging
from datetime import datetime as Datetime
from threading import Thread

import requests
from bs4 import BeautifulSoup

import config
from proxy_filter import filter_proxy, Proxy
from scraper_utils import scrape_free_proxy_list_net, is_updated_github, is_updated
from scraper_utils import type_anonymity_set, type_anonymity_country_set

logging.basicConfig(level=logging.INFO)


def clarketm():  # github.com/clarketm/proxy-list
    # as known as spys.me
    # include:
    # pubproxy.com
    # spys.one
    logging.info('%s: starting' % clarketm.__name__)
    if 'http' not in config.proxy_type and 'https' not in config.proxy_type:
        return
    if not is_updated_github('clarketm/proxy-list', 'proxy-list.txt'):
        logging.info('%s: no update' % clarketm.__name__)
        return
    r = requests.get('https://github.com/clarketm/proxy-list/raw/master/proxy-list.txt')
    lines = r.text.splitlines()[9:]
    logging.info('%s: %d proxies' % (clarketm.__name__, len(lines)))
    for line in lines:
        p = line.split(' ')
        proxy = Proxy()
        proxy.address = p[0].strip()
        p = p[1].split('-')
        if len(p) < 1:  # no country
            continue
        proxy.country = p[0].strip()
        if len(p) < 2:  # no anonymity
            continue
        if 'N' in p[1]:
            proxy.anonymity = 'transparent'
        elif 'A' in p[1]:
            proxy.anonymity = 'anonymous'
        elif 'H' in p[1]:
            proxy.anonymity = 'elite'
        else:
            raise ValueError('Unknown anonymity: ' + p[1])
        if len(p) < 3:  # no type
            proxy.type = 'http'
        elif 'S' in p[2]:  # https
            proxy.type = 'https'
        else:
            raise ValueError('Unknown proxy type: ' + p[2])
        filter_proxy(proxy)
    logging.info('%s: ending' % clarketm.__name__)


def fate0():  # github.com/fate0/proxylist
    # as known as proxylist.fatezero.org
    logging.info('%s: starting' % fate0.__name__)
    if not is_updated_github('fate0/proxylist', 'proxy.list'):
        logging.info('%s: no update' % fate0.__name__)
        return
    r = requests.get('https://github.com/fate0/proxylist/raw/master/proxy.list')
    lines = r.text.splitlines()
    logging.info('%s: %d proxies' % (fate0.__name__, len(lines)))
    for line in lines:
        if not line:
            continue
        j = json.loads(line)
        proxy = Proxy()
        proxy.address = j['host'] + ':' + str(j['port'])
        proxy.type = j['type']
        proxy.country = j['country']
        if 'high' in j['anonymity']:
            proxy.anonymity = 'elite'
        else:
            proxy.anonymity = j['anonymity']
        filter_proxy(proxy)
    logging.info('%s: ending' % fate0.__name__)


def free_proxy_list_net():  # free-proxy-list.net
    logging.info('%s: starting' % free_proxy_list_net.__name__)
    if 'transparent' not in config.proxy_anonymity:
        scrape_free_proxy_list_net('https://free-proxy-list.net/anonymous-proxy.html')
    if (not config.proxy_country or 'UK' in config.proxy_country) and 'UK' not in config.proxy_country_exclude:
        scrape_free_proxy_list_net('https://free-proxy-list.net/uk-proxy.html')
    scrape_free_proxy_list_net('https://free-proxy-list.net')
    logging.info('%s: ending' % free_proxy_list_net.__name__)


def hookzof():  # github.com/hookzof/socks5_list
    logging.info('%s: starting' % hookzof.__name__)
    if 'socks5' not in config.proxy_type:
        return
    if not is_updated_github('hookzof/socks5_list', 'tg/socks.json'):
        logging.info('%s: no update' % hookzof.__name__)
        return
    r = requests.get('https://github.com/hookzof/socks5_list/raw/master/tg/socks.json')
    jsons = r.json()
    logging.info('%s: %d proxies' % (hookzof.__name__, len(jsons)))
    for j in jsons:
        timestamp = int(j['unix'])
        dt = Datetime.fromtimestamp(timestamp)
        if not is_updated(dt):
            continue
        proxy = Proxy()
        proxy.address = j['ip'] + ':' + j['port']
        proxy.type = 'socks5'
        proxy.country = j['country']
        proxy.anonymity = 'elite'
        filter_proxy(proxy)
    logging.info('%s: ending' % hookzof.__name__)


def proxy_list_download():  # proxy-list.download
    logging.info('%s: staring' % proxy_list_download.__name__)
    for setting in type_anonymity_country_set:
        params = {'type': setting[0]}
        if setting[1]:
            params['anon'] = setting[1]
        if setting[2]:
            params['country'] = setting[2]
        logging.info('%s: %s' % (proxy_list_download.__name__, str(params)))
        r = requests.get('https://www.proxy-list.download/api/v1/get', params=params)
        lines = r.text.splitlines()
        logging.info('%s: %d proxies' % (proxy_list_download.__name__, len(lines)))
        for line in lines:
            address = line.strip()
            if address:
                proxy = Proxy()
                proxy.address = address
                proxy.type = setting[0]
                if setting[1]:
                    proxy.anonymity = setting[1]
                if setting[2]:
                    proxy.country = setting[2]
                filter_proxy(proxy)
    logging.info('%s: ending' % proxy_list_download.__name__)


def proxyscrape_com():  # proxyscrape.com
    logging.info('%s: starting' % proxyscrape_com.__name__)
    for setting in type_anonymity_set:
        params = {'request': 'getproxies', 'proxytype': setting[0]}
        if 'http' == params['proxytype']:
            params['ssl'] = 'no'
        elif 'https' == params['proxytype']:
            params['proxytype'] = 'http'
            params['ssl'] = 'yes'
        if setting[1]:
            params['anonymity'] = setting[1]
        if config.proxy_country:
            params['country'] = ','.join(config.proxy_country)
        logging.info('%s: %s' % (proxyscrape_com.__name__, str(params)))
        r = requests.get('https://api.proxyscrape.com', params=params)
        lines = r.text.splitlines()
        logging.info('%s: %d proxies' % (proxyscrape_com.__name__, len(lines)))
        for line in lines:
            address = line.strip()
            if address:
                proxy = Proxy()
                proxy.address = address
                proxy.type = setting[0]
                if setting[1]:
                    proxy.anonymity = setting[1]
                if 1 == len(config.proxy_country):
                    proxy.country = config.proxy_country
                filter_proxy(proxy)
    logging.info('%s: ending' % proxyscrape_com.__name__)


def socks_proxy_net():  # socks-proxy.net
    logging.info('%s: starting' % socks_proxy_net.__name__)
    if 'socks4' not in config.proxy_type and 'socks5' not in config.proxy_type:
        return
    r = requests.get('https://socks-proxy.net')
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', attrs={'id': 'proxylisttable'})
    rows = table.find_all("tr")
    logging.info('%s: %d proxies' % (socks_proxy_net.__name__, len(rows)))
    for row in rows:
        cells = row.find_all("td")
        if len(cells) == 8:
            address = cells[0].text
            address += ':' + cells[1].text
            proxy = Proxy()
            proxy.address = address.strip('&nbsp;')
            proxy.type = cells[4].text.lower().strip('&nbsp;')
            proxy.anonymity = 'elite'
            proxy.country = cells[2].text.upper().strip('&nbsp;')
            filter_proxy(proxy)
    logging.info('%s: ending' % proxyscrape_com.__name__)


def sslproxies_org():  # sslproxies.org
    logging.info('%s: starting' % sslproxies_org.__name__)
    if 'https' not in config.proxy_type:
        return
    scrape_free_proxy_list_net('https://sslproxies.org')
    logging.info('%s: ending' % sslproxies_org.__name__)


def us_proxy_org():  # us-proxy.org
    logging.info('%s: starting' % us_proxy_org.__name__)
    if config.proxy_country and 'US' not in config.proxy_country:
        return
    if 'US' in config.proxy_country_exclude:
        return
    scrape_free_proxy_list_net('https://us-proxy.org')
    logging.info('%s: starting' % us_proxy_org.__name__)


Thread(target=clarketm).start()
Thread(target=fate0).start()
Thread(target=free_proxy_list_net).start()
Thread(target=hookzof).start()
Thread(target=proxy_list_download).start()
Thread(target=proxyscrape_com).start()
Thread(target=socks_proxy_net).start()
Thread(target=sslproxies_org).start()
Thread(target=us_proxy_org).start()
