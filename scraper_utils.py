from datetime import datetime as Datetime
from itertools import product as Product

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
    if not any('http' in pt for pt in config.proxy_type):
        return
    page = requests.get(url)
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


def is_updated(timestamp: Datetime) -> bool:
    now = Datetime.now()
    return (now - timestamp).seconds < 3600


def is_updated_github(repo: str, path: str) -> bool:
    repo: Repository = Github().get_repo(repo)
    commits: PaginatedList[Commit] = repo.get_commits(path=path)
    return is_updated(commits[0].commit.author.date)
