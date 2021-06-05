import threading

import requests
from bs4 import BeautifulSoup

import config


def filter_proxy():
    pass


# sslproxies.org
# only https proxies
def scrape_sslproxies_org():
    if 'http' not in config.proxy_type and 'https' not in config.proxy_type:
        return
    page = requests.get('https://sslproxies.org')
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find('table', attrs={'id': 'proxylisttable'})
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 8:
            proxy = cells[0].text
            proxy += ':' + cells[1].text
            proxy = proxy.replace('&nbsp;', '')
            country = cells[2].text.replace('&nbsp;', '').lower()
            anonymity = cells[4].text.replace('&nbsp;', '').replace(' proxy', '')
            filter_proxy()


threading.Thread(target=scrape_sslproxies_org).start()
