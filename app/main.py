import typer
from config.loader import load_config
from collector.saxo import SaxoCollector
from storage.store import SqliteStore
from backtest.replay import run_backtest

app = typer.Typer()

@app.command()
def collect():
    settings = load_config()
    store = SqliteStore(settings.storage.database)
    collector = SaxoCollector(settings.collector, store)
    collector.on_tick(lambda t: print(t))
    collector.run()

@app.command()
def backtest():
    run_backtest()

if __name__ == '__main__':
    app()
