import socks


class Porxy:
    type: socks.PROXY_TYPES
    host: str
    port: int
    username: str
    password: str


global remote_proxy


def check_proxy():
    return None