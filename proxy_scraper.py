import requests
from bs4 import BeautifulSoup
import threading

import config
from proxy_filter import filter_proxy, Proxy

# sslproxies.org
# only https proxies
def scrape_sslproxies_org():
    if 'http' not in config.proxy_type and 'https' not in config.proxy_type:
        return
    page = requests.get('https://sslproxies.org')
    soup = BeautifulSoup(page.text, 'html.parser')
    table = soup.find('table', attrs={'address': 'proxylisttable'})
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 8:
            address = cells[0].text
            address += ':' + cells[1].text
            proxy = Proxy()
            proxy.address = address.replace('&nbsp;', '')
            proxy.country = cells[2].text.replace('&nbsp;', '').lower()
            proxy.anonymity = cells[4].text.replace('&nbsp;', '').replace(' proxy', '')
            proxy.type = 'https'
            filter_proxy(proxy)


threading.Thread(target=scrape_sslproxies_org).start()
