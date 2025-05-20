from abc import ABC, abstractmethod
from storage.store import SqliteStore

class ITickSource(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def on_tick(self, callback):
        pass

class SaxoCollector(ITickSource):
    def __init__(self, config, store: SqliteStore):
        self.endpoint = config.endpoint
        self.symbols = config.symbols
        self.store = store

    def connect(self):
        # TODO: Connect to Saxo WebSocket at self.endpoint
        print(f"Connecting to {self.endpoint} for symbols {self.symbols}")

    def on_tick(self, callback):
        # TODO: Register tick callback
        self.callback = callback

    def run(self):
        self.connect()
        # Example: simulate incoming ticks
        import datetime, time
        for i in range(5):
            tick = {
                'timestamp': datetime.datetime.now().isoformat(),
                'bid': 1.1 + i*0.001,
                'ask': 1.1 + i*0.001 + 0.0001,
                'volume': 100 + i
            }
            self.store.insert_tick(tick)
            self.callback(tick)
            time.sleep(1)
