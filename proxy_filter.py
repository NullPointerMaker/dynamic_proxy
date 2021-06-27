import logging
from multiprocessing import Lock as ProcessLock
from threading import Lock as ThreadLock

from peewee import SqliteDatabase, Model, CharField, FixedCharField, IntegrityError, InterfaceError, OperationalError

import config

db = SqliteDatabase('pool.db')
threadLock = ThreadLock()
processLock = ProcessLock()


def lock():
    threadLock.acquire()
    processLock.acquire()


def unlock():
    processLock.release()
    threadLock.release()


class Proxy(Model):
    address = CharField(unique=True, primary_key=True)
    type = CharField(max_length=6)
    anonymity = CharField(max_length=11)
    country = FixedCharField(max_length=2, null=True)

    class Meta:
        database = db


Proxy.create_table()


def delete_proxy(proxy: Proxy):
    lock()
    try:
        proxy.delete_instance()
    except OperationalError as oe:
        logging.exception(oe)
    finally:
        unlock()


def is_valid_address(address: str) -> bool:
    try:
        r = address.split(':')
        if len(r) != 2:
            return False
        port = int(r[1])
        if port < 0 or port > 65535:
            return False
        for i in r[0].split('.'):
            i = int(i)
            if i < 0 or i > 255:
                return False
    except (ValueError, TypeError):
        return False
    return True


def is_valid(proxy: Proxy) -> bool:
    if not is_valid_address(str(proxy.address)):
        return False
    if proxy.type not in config.proxy_type:
        return False
    if proxy.anonymity not in config.proxy_anonymity:
        return False
    if config.proxy_country and proxy.country not in config.proxy_country:
        return False
    if config.proxy_country_exclude and proxy.country in config.proxy_country_exclude:
        return False
    return True


def filter_proxy(proxy: Proxy):
    if 'socks' in proxy.type and not proxy.anonymity:
        proxy.anonymity = 'elite'
    if is_valid(proxy):
        lock()
        try:
            proxy.save(force_insert=True)
        except IntegrityError:
            pass
        except InterfaceError as ie:
            # Error binding parameter 0 - probably unsupported type.
            # dont know why
            logging.exception(ie)
        finally:
            unlock()
        logging.debug('%s saved' % proxy.address)
