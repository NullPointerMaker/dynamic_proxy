import asyncio
import logging
import socket
from asyncio import StreamReader, StreamWriter, StreamReaderProtocol

import socks  # pysocks

import config
from proxy_checker import get_checked_proxy as checked_proxy, rotate_proxy

logging.basicConfig(level=logging.INFO)

old_getaddrinfo = socket.getaddrinfo


def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]


socket.getaddrinfo = new_getaddrinfo


async def tunnel(from_client, to_client, from_server, to_server):
    async def io_copy(reader: StreamReader, writer: StreamWriter):
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
        writer.close()

    asyncio.ensure_future(io_copy(from_client, to_server))
    asyncio.ensure_future(io_copy(from_server, to_client))


async def conn_server(server_host: str, server_port: int,
                      limit=2 ** 16) -> (StreamReader, StreamWriter):
    sock = socks.socksocket()
    sock.set_proxy(proxy_type=checked_proxy().get('type'),
                   addr=checked_proxy().get('host'),
                   port=checked_proxy().get('port'),
                   username=checked_proxy().get('username'),
                   password=checked_proxy().get('password'))
    sock.connect((server_host, server_port))

    loop = asyncio.get_event_loop()
    from_server = StreamReader(limit=limit, loop=loop)
    protocol = StreamReaderProtocol(from_server, loop=loop)
    transport, _ = await loop.create_connection(lambda: protocol, sock=sock)
    to_server = StreamWriter(transport, protocol, from_server, loop)
    return from_server, to_server


def get_conn_prop(headers: list[bytes]) -> (bool, str, int):
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
            if line == b'\r\n':
                break
            http_headers.append(line)
        is_connect, server_host, server_port = get_conn_prop(http_headers)
    except (IOError, ValueError) as e:
        logging.error(e)
        to_client.close()
        return
    from_server, to_server = await conn_server(
        server_host=server_host,
        server_port=server_port
    )
    if is_connect:
        to_client.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
    else:
        to_server.write(b''.join(http_headers))
    asyncio.ensure_future(tunnel(from_client, to_client, from_server, to_server))


rotate_proxy()
server = asyncio.start_server(conn_client,
                              host=config.local_host,
                              port=config.local_port,
                              reuse_address=True,
                              reuse_port=True)
