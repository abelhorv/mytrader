import pytest
from storage.store import SqliteStore
from config.loader import load_config
import os

def test_sqlite_store_insert_and_fetch(tmp_path):
    db_file = tmp_path / "test.db"
    settings = load_config(path="config/config.yaml")
    store = SqliteStore(str(db_file))
    tick = {'timestamp': '2025-01-01T00:00:00', 'bid': 1.0, 'ask': 1.0, 'volume': 100}
    store.insert_tick(tick)
    ticks = store.fetch_ticks('2025-01-01T00:00:00')
    assert len(ticks) >= 1
