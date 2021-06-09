import logging
from datetime import datetime as Datetime

import requests
from bs4 import BeautifulSoup
from github import Github
from github.Commit import Commit
from github.PaginatedList import PaginatedList
from github.Repository import Repository

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
            proxy.anonymity = cells[4].text.lower().strip('&nbsp;').strip(' proxy')
            proxy.country = cells[2].text.upper().strip('&nbsp;')
            filter_proxy(proxy)
    logging.info('%s ending' % url)


def is_updated(timestamp: Datetime) -> bool:
    now = Datetime.now()
    return (now - timestamp).seconds < 3600


def is_updated_github(repo: str, path: str) -> bool:
    repo: Repository = Github().get_repo(repo)
    commits: PaginatedList[Commit] = repo.get_commits(path=path)
    return is_updated(commits[0].commit.author.date)
