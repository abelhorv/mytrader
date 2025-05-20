import datetime
from collections import deque

class CandleBuilder:
    def __init__(self, interval_seconds):
        self.interval = datetime.timedelta(seconds=interval_seconds)
        self.current_start = None
        self.open = self.high = self.low = self.close = None
        self.volume = 0.0

    def add_tick(self, tick):
        ts = datetime.datetime.fromisoformat(tick['timestamp'])
        mid = (tick['bid'] + tick['ask']) / 2.0
        if self.current_start is None:
            self.current_start = ts.replace(second=0, microsecond=0)
            self.open = self.high = self.low = self.close = mid
            self.volume = tick['volume']
            return None

        if ts >= self.current_start + self.interval:
            candle = {
                'timestamp': self.current_start.isoformat(),
                'open': self.open,
                'high': self.high,
                'low': self.low,
                'close': self.close,
                'volume': self.volume
            }
            # start new
            periods = int((ts - self.current_start).total_seconds() // self.interval.total_seconds())
            self.current_start += self.interval * periods
            self.open = self.high = self.low = self.close = mid
            self.volume = tick['volume']
            return candle

        # within interval
        self.high = max(self.high, mid)
        self.low = min(self.low, mid)
        self.close = mid
        self.volume += tick['volume']
        return None

class MultiIntervalCandleBuilder:
    def __init__(self, intervals):
        self.builders = {i: CandleBuilder(i) for i in intervals}

    def add_tick(self, tick):
        completed = {}
        for interval, builder in self.builders.items():
            c = builder.add_tick(tick)
            if c:
                completed[interval] = c
        return completed
