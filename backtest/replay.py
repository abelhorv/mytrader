from storage.store import SqliteStore
from aggregator.candle_builder import MultiIntervalCandleBuilder
from strategy.strategies import RsiStrategy
from config.loader import load_config

def run_backtest():
    settings = load_config()
    store = SqliteStore(settings.storage.database)
    builder = MultiIntervalCandleBuilder(settings.aggregator.intervals)
    strategy = RsiStrategy(settings.strategy.rsi_period)
    ticks = store.fetch_ticks(settings.backtest.start)
    history = []

    for ts, bid, ask, volume in ticks:
        tick = {'timestamp': ts, 'bid': bid, 'ask': ask, 'volume': volume}
        candles = builder.add_tick(tick)
        if candles.get(60):
            history.append(candles[60])
        signal = strategy.generate_signal(history, tick)
        print(f"{ts}: {signal}")
