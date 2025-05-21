# storage/store.py
from abc import ABC, abstractmethod
import sqlite3
import psycopg2
from config.loader import load_config

class IStore(ABC):
    @abstractmethod
    def insert_tick(self, tick): ...
    @abstractmethod
    def fetch_ticks(self, since): ...

class SqliteStore(IStore):
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def insert_tick(self, tick):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO pricesandvolume(timestamp,bid,ask,volume) VALUES (?,?,?,?)",
            (tick['timestamp'], tick['bid'], tick['ask'], tick['volume'])
        )
        self.conn.commit()

    def fetch_ticks(self, since):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT timestamp, bid, ask, volume FROM pricesandvolume WHERE timestamp >= ? ORDER BY timestamp",
            (since,)
        )
        return cur.fetchall()

class PostgresStore(IStore):
    def __init__(self, cfg):
        self.conn = psycopg2.connect(
            dbname=cfg['dbname'], user=cfg['user'], password=cfg['password'],
            host=cfg['host'], port=cfg['port']
        )

    def insert_tick(self, tick):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO pricesandvolume(timestamp,bid,ask,volume) VALUES (%s,%s,%s,%s)",
            (tick['timestamp'], tick['bid'], tick['ask'], tick['volume'])
        )
        self.conn.commit()

    def fetch_ticks(self, since):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT timestamp, bid, ask, volume FROM pricesandvolume WHERE timestamp >= %s ORDER BY timestamp",
            (since,)
        )
        return cur.fetchall()

def get_store():
    settings = load_config()
    if settings.storage.db_config:
        return PostgresStore(settings.storage.db_config)
    else:
        return SqliteStore(settings.storage.database)

