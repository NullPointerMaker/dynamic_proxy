import asyncio
import logging
import socket
from asyncio import StreamReader, StreamWriter
from threading import Thread
from typing import List

import config
from proxy_checker import get_checked_proxy as checked_proxy, rotate_proxy

logging.basicConfig(level=logging.INFO)

old_getaddrinfo = socket.getaddrinfo


def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]


socket.getaddrinfo = new_getaddrinfo  # force IPv4


async def tunnel(from_client, to_client, from_server, to_server):
    async def io_copy(reader: StreamReader, writer: StreamWriter):
        logging.debug('%s: starting' % tunnel.__name__)
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
        writer.close()
        logging.debug('%s: ending' % tunnel.__name__)

    asyncio.ensure_future(io_copy(from_client, to_server))
    asyncio.ensure_future(io_copy(from_server, to_client))


async def conn_server(server_host: str, server_port: int) -> (StreamReader, StreamWriter):
    if server_host in config.bypass_proxy:
        return await asyncio.open_connection(host=server_host, port=server_port)
    logging.info('proxy: %s:%d' % (checked_proxy().proxy_host, checked_proxy().proxy_port))
    sock = await checked_proxy().connect(server_host, server_port)
    return await asyncio.open_connection(sock=sock)


def get_conn_prop(headers: List[bytes]) -> (bool, str, int):
    header: str = headers[0].decode()
    method, url, version = header.split(' ', 2)
    is_connect = method.upper() == 'CONNECT'
    if is_connect:
        host, port = url.split(':', 1)
    else:
        host_port: str = ''
        headers = headers[1:]
        for h in headers:
            header = h.decode().strip()
            if header[0:5].upper() != 'HOST:':
                continue
            host_port = header[5:].strip()
        if not host_port:
            raise ValueError('No HTTP Host header')
        if ':' not in host_port:
            host = host_port
            port = '80'
        else:
            host, port = host_port.split(':', 1)
    port = int(port)
    return is_connect, host, int(port)


async def conn_client(reader: StreamReader, writer: StreamWriter):
    from_client, to_client = reader, writer
    try:
        http_headers: list[bytes] = []
        while True:
            line = await from_client.readline()
            http_headers.append(line)
            if not line or line == b'\r\n':
                break
        is_connect, server_host, server_port = get_conn_prop(http_headers)
    except (IOError, ValueError) as e:
        logging.error(e)
        to_client.close()
        return
    logging.info('server: %s %d' % (server_host, server_port))
    from_server, to_server = await conn_server(server_host, server_port)
    if is_connect:
        to_client.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
    else:
        to_server.write(b''.join(http_headers))
    asyncio.ensure_future(tunnel(from_client, to_client, from_server, to_server))


Thread(target=rotate_proxy).start()
event_loop = asyncio.get_event_loop()
server = asyncio.start_server(conn_client,
                              host=config.local_host,
                              port=config.local_port)
server = event_loop.run_until_complete(server)
logging.info('HTTP proxy: %s:%d' % (config.local_host, config.local_port))
event_loop.run_forever()
