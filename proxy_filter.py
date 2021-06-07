from peewee import SqliteDatabase, Model, CharField, FixedCharField, IntegrityError

import config

db = SqliteDatabase(config.database_file)


class Proxy(Model):
    address = CharField(unique=True, primary_key=True)
    type = CharField(max_length=10)
    anonymity = CharField(max_length=10)
    country = FixedCharField(max_length=2)

    class Meta:
        database = db


Proxy.create_table()


def is_valid(proxy: Proxy) -> bool:
    if 'socks' in proxy.type and not proxy.anonymity:
        proxy.anonymity = 'elite'
    if config.proxy_type and proxy.type not in config.proxy_type:
        return False
    if config.proxy_anonymity and proxy.anonymity not in config.proxy_anonymity:
        return False
    if config.proxy_country and proxy.country not in config.proxy_country:
        return False
    if proxy.country in config.proxy_country_exclude:
        return False
    return True


def filter_proxy(proxy: Proxy):
    if is_valid(proxy):
        try:
            proxy.save(force_insert=True)
        except IntegrityError:
            pass
