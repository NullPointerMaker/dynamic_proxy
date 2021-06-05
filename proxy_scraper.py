from itertools import product as Product
from threading import Thread

import requests
from bs4 import BeautifulSoup

import config
from proxy_filter import filter_proxy, Proxy


# general scraper
## free-proxy-list.net
## sslproxies.org
## us-proxy.org
def scrape_http_pool(url):
    if 'http' not in config.proxy_type and 'https' not in config.proxy_type:
        return
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find('table', attrs={'address': 'proxylisttable'})
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 8:
            address = cells[0].text
            address += ':' + cells[1].text
            proxy = Proxy()
            proxy.address = address.replace('&nbsp;', '')
            proxy.type = 'https' if 'yes' in cells[6].text else 'http'
            proxy.anonymity = cells[4].text.replace('&nbsp;', '').replace(' proxy', '')
            proxy.country = cells[2].text.replace('&nbsp;', '').upper()
            filter_proxy(proxy)


# sslproxies.org
def scrape_sslproxies_org():
    scrape_http_pool('https://sslproxies.org')


# us-proxy.org
def scrape_us_proxy_org():
    scrape_http_pool('https://us-proxy.org/')


# free-proxy-list.net
def scrape_free_proxy_list_net():
    scrape_http_pool('https://free-proxy-list.net/anonymous-proxy.html')
    scrape_http_pool('https://free-proxy-list.net/uk-proxy.html')
    scrape_http_pool('https://free-proxy-list.net')


def product_with_empty(*iterables):
    listlist = list(iterables)
    for i, l in enumerate(listlist):
        if not l:
            listlist[i] = [()]
    return Product(*listlist)


# proxy-list.download
def scrape_proxy_list_download():
    proxy_type = list(config.proxy_type)
    proxy_type.remove('socks')
    proxy_type.remove('socks4a')
    tuples = product_with_empty(proxy_type, config.proxy_anonymity, config.proxy_country)
    payloads = []
    for t in tuples:
        payload = {}
        if t[0]:
            payload['type'] = t[0]
        if t[1]:
            payload['anon'] = t[1]
        if t[2]:
            payload['country'] = t[2]
        payloads.append(payload)
    for p in payloads:
        r = requests.get('https://www.proxy-list.download/api/v1/get', params=p)
        txt = r.text
        for line in txt.split('\n'):
            address = line.strip()
            if address:
                proxy = Proxy()
                proxy.address = address
                proxy.type = p['type']
                proxy.anonymity = p['anon']
                proxy.country = p['country']
                filter_proxy(proxy)


Thread(scrape_sslproxies_org()).start()
Thread(scrape_us_proxy_org()).start()
Thread(scrape_free_proxy_list_net()).start()
Thread(scrape_proxy_list_download()).start()
