# app/main.py
import typer
from config.loader import load_config
from collector.saxo import SaxoCollector
from storage.store import get_store
from aggregator.candle_builder import MultiIntervalCandleBuilder
from strategy.strategies import ParametrizedStrategy
from backtest.replay import run_backtest

app = typer.Typer()

@app.command()
def collect():
    settings = load_config()
    store    = get_store()
    collector= SaxoCollector(settings.collector, store)
    builder  = MultiIntervalCandleBuilder(settings.aggregator.intervals)
    strategy = ParametrizedStrategy(settings.strategy)

    def on_tick(tick):
        store.insert_tick(tick)
        completed = builder.add_tick(tick)
        if 60 in completed:
            # e.g. keep only 1m history for simplicity
            history.append(completed[60])
            signal = strategy.generate_signal(history, tick)
            print(f"{tick['timestamp']}: {signal}")

    collector.on_tick(on_tick)
    collector.run()

@app.command()
def backtest():
    run_backtest()

if __name__ == "__main__":
    app()
