# valid option: http, https, socks4, socks5
# type can not be null
# http not include https
proxy_type = ('https', 'socks4', 'socks5')
# valid option: transparent, anonymous, elite
# anonymity not set = all
proxy_anonymity = ('anonymous', 'elite')
# country not set = all
proxy_country = ()
proxy_country_exclude = ('CN', 'MO')

database_file = 'pool.db'

local_host = '127.0.0.1'
local_port = 1080

rotate_interval = 600
