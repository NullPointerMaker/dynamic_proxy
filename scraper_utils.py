from itertools import product as Product

import requests
from bs4 import BeautifulSoup

import config
from proxy_filter import Proxy, filter_proxy


# free-proxy-list.net
# sslproxies.org
# us-proxy.org
def scrape_free_proxy_list_net(url):
    if not any('http' in pt for pt in config.proxy_type):
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


def product_with_empty(*iterables):
    lists = list(iterables)
    for i, l in enumerate(lists):
        if not l:
            lists[i] = [()]
    return Product(*lists)
