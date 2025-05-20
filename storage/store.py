from abc import ABC, abstractmethod
import sqlite3

class IStore(ABC):
    @abstractmethod
    def insert_tick(self, tick):
        pass

    @abstractmethod
    def fetch_ticks(self, since):
        pass

class SqliteStore(IStore):
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def insert_tick(self, tick):
        # Insert tick into SQLite
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
