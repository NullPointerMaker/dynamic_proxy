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


def is_valid(proxy: Proxy) -> bool:
    if 'socks' in proxy.type and not proxy.anonymity:
        proxy.anonymity = 'elite'
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
