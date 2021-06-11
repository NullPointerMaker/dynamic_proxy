# valid option: http, https, socks4, socks5
# type can not be null
# http not include https
proxy_type = ['https', 'socks4', 'socks5']
# valid option: transparent, anonymous, elite
# anonymity can not set
proxy_anonymity = ['anonymous', 'elite']
# country not set = all
proxy_country = []
proxy_country_exclude = ['CN', 'MO']

local_host = '127.0.0.1'
local_port = 3128

rotate_interval = 600
timeout = 5
