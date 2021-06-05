from peewee import SqliteDatabase, Model, CharField, FixedCharField, IntegrityError

import config

db = SqliteDatabase(config.datebase_file)


class Proxy(Model):
    address = CharField(unique=True, primary_key=True)
    type = CharField(max_length=10)
    anonymity = CharField(max_length=10)
    country = FixedCharField(max_length=2)

    class Meta:
        database = db


Proxy.create_table()


def filter_proxy(proxy: Proxy):
    if config.proxy_type and proxy.type not in config.proxy_type:
        return
    if config.proxy_anonymity and proxy.anonymity not in config.proxy_anonymity:
        return
    if config.proxy_country and proxy.country not in config.proxy_country:
        return
    if proxy.country in config.proxy_country_exclude:
        return
    try:
        proxy.save(force_insert=True)
    except IntegrityError:
        pass
