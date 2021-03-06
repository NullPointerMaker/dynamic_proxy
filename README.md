# Dynamic Proxy
* Scrape proxies from multi pools.
* Filter by types, anonymity, countries.
* Check anonymity, reachability to websites.
* Serve as a HTTPS proxy, tunnel to a periodically rotating random remote proxy.

## Install
1. Install Python 3.6.8+.
2. Install requirements:
   ```
   pip3 install -r requirements.txt
   ```

## Usage
1. Modify `config.py` according to your needs.
2. Scrape proxies from multi pools:
   ```
   python3 pool_scraper.py
   ```
   If you need to run periodically, please use the job scheduler of the operating system.  
   It is recommended to scrape hourly.
3. Run a dynamic chained HTTPS proxy:
   ```
   python3 dynamic_proxy.py
   ```
   Which will tunnel to a random proxy from those scraped before, rotate periodically.

## Pools
* [clarketm/proxy-list](https://github.com/clarketm/proxy-list) (AKA spys.me)  
  * pubproxy.com
  * spys.one
* [fate0/proxylist](https://github.com/fate0/proxylist) (AKA proxylist.fatezero.org)
* free-proxy-list.net (include several subsites)
* [hookzof/socks5_list](https://github.com/hookzof/socks5_list)
* proxy-list.download
* proxyscrape.com
* socks-proxy.net (subsite of free-proxy-list.net)
* sslproxies.org (subsite of free-proxy-list.net)
* us-proxy.org (subsite of free-proxy-list.net)