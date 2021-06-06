import asyncio
import logging
from asyncio import StreamReader, StreamWriter, StreamReaderProtocol
from threading import Thread

import socks  # pysocks

import config
from proxy_checker import remote_proxy as proxy, check_proxy

logging.basicConfig(level=logging.INFO)


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
    sock.set_proxy(proxy_type=proxy.type,
                   addr=proxy.host,
                   port=proxy.port,
                   username=proxy.username,
                   password=proxy.password)
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
        for h in headers[1:]:
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
        while (line := await from_client.readline()) != b'\r\n':
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


Thread(check_proxy()).start()
server = asyncio.start_server(conn_client,
                              host=config.local_host,
                              port=config.local_port,
                              reuse_address=True,
                              reuse_port=True)
