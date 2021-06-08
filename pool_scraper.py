import json
from datetime import datetime as Datetime
from itertools import product as Product
from threading import Thread

import requests
from bs4 import BeautifulSoup

import config
from proxy_filter import filter_proxy, Proxy
from scraper_utils import scrape_free_proxy_list_net, is_updated_github, is_updated


def clarketm():  # github.com/clarketm/proxy-list
    # as known as spys.me
    # include:
    # pubproxy.com
    # spys.one
    if 'http' not in config.proxy_type and 'https' not in config.proxy_type:
        return
    if not is_updated_github('clarketm/proxy-list', 'proxy-list.txt'):
        return
    r = requests.get('https://github.com/clarketm/proxy-list/raw/master/proxy-list.txt')
    lines = r.text.splitlines()[9:]
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


def fate0():  # github.com/fate0/proxylist
    # as known as proxylist.fatezero.org
    if not is_updated_github('fate0/proxylist', 'proxy.list'):
        return
    r = requests.get('https://github.com/fate0/proxylist/raw/master/proxy.list')
    lines = r.text.splitlines()
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


def free_proxy_list_net():  # free-proxy-list.net
    if 'transparent' not in config.proxy_anonymity:
        scrape_free_proxy_list_net('https://free-proxy-list.net/anonymous-proxy.html')
    if (not config.proxy_country or 'UK' in config.proxy_country) and 'UK' not in config.proxy_country_exclude:
        scrape_free_proxy_list_net('https://free-proxy-list.net/uk-proxy.html')
    scrape_free_proxy_list_net('https://free-proxy-list.net')


def hookzof():  # github.com/hookzof/socks5_list
    if 'socks5' not in config.proxy_type:
        return
    if not is_updated_github('hookzof/socks5_list', 'tg/socks.json'):
        return
    r = requests.get('https://github.com/hookzof/socks5_list/raw/master/tg/socks.json')
    jsons = r.json()
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


def proxy_list_download():  # proxy-list.download
    if config.proxy_country:
        tuples = Product(config.proxy_type, config.proxy_anonymity, config.proxy_country)
    else:
        tuples = Product(config.proxy_type, config.proxy_anonymity)
    for t in tuples:
        paras = {'type': t[0], 'anon': t[1]}
        if len(t) > 2:
            paras['country'] = t[2]
        r = requests.get('https://www.proxy-list.download/api/v1/get', params=paras)
        lines = r.text.splitlines()
        for line in lines:
            address = line.strip()
            if address:
                proxy = Proxy()
                proxy.address = address
                proxy.type = paras['type']
                proxy.anonymity = paras['anon']
                if 'country' in paras:
                    proxy.country = paras['country']
                filter_proxy(proxy)


def proxyscrape_com():  # proxyscrape.com
    if config.proxy_country:
        tuples = Product(config.proxy_type, config.proxy_anonymity, config.proxy_country)
    else:
        tuples = Product(config.proxy_type, config.proxy_anonymity)
    for t in tuples:
        paras = {'request': 'getproxies', 'status': '1', 'proxytype': t[0], 'anonymity': t[1]}
        if 'http' == paras['proxytype']:
            paras['proxytype'] = 'http'
            paras['ssl'] = 'no'
        elif 'https' == paras['proxytype']:
            paras['proxytype'] = 'http'
            paras['ssl'] = 'yes'
        if len(t) > 2:
            paras['country'] = t[2]
        r = requests.get('https://api.proxyscrape.com', params=paras)
        lines = r.text.splitlines()
        for line in lines:
            address = line.strip()
            if address:
                proxy = Proxy()
                proxy.address = address
                proxy.type = t[0]
                proxy.anonymity = paras['anonymity']
                if 'country' in paras:
                    proxy.country = paras['country']
                filter_proxy(proxy)


def socks_proxy_net():  # socks-proxy.net
    if 'socks4' not in config.proxy_type and 'socks5' not in config.proxy_type:
        return
    page = requests.get('https://socks-proxy.net')
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find('table', attrs={'address': 'proxylisttable'})
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) == 8:
            address = cells[0].text
            address += ':' + cells[1].text
            proxy = Proxy()
            proxy.address = address.replace('&nbsp;', '')
            proxy.type = cells[4].text.replace('&nbsp;', '').lower()
            proxy.anonymity = 'elite'
            proxy.country = cells[2].text.replace('&nbsp;', '').upper()
            filter_proxy(proxy)


def sslproxies_org():  # sslproxies.org
    if 'https' not in config.proxy_type:
        return
    scrape_free_proxy_list_net('https://sslproxies.org')


def us_proxy_org():  # us-proxy.org
    if config.proxy_country and 'US' not in config.proxy_country:
        return
    if 'US' in config.proxy_country_exclude:
        return
    scrape_free_proxy_list_net('https://us-proxy.org')


Thread(clarketm()).start()
Thread(fate0()).start()
Thread(free_proxy_list_net()).start()
Thread(hookzof()).start()
Thread(proxy_list_download()).start()
Thread(proxyscrape_com()).start()
Thread(socks_proxy_net()).start()
Thread(sslproxies_org()).start()
Thread(us_proxy_org()).start()
