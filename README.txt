# Forex Trading Bot 

## High-Level Architecture

1. **Data Ingestion Layer** (`collector/`):  
   Connects to live feeds via WebSocket, normalizes raw ticks, and writes to storage.

2. **Persistence Layer** (`storage/`):  
   Abstracts database operations (inserts, queries) using `IStore` with SQLite implementation.

3. **Candle Aggregation Layer** (`aggregator/`):  
   Builds multi-interval OHLCV candles in real-time based on tick data.

4. **Indicator & Strategy Layer** (`strategy/`):  
   Computes technical indicators (RSI) and generates signals via strategy classes.

5. **Execution & Risk Management** (`executor/`):  
   Manages order placement with slippage and basic risk checks.

6. **Backtesting & Simulation** (`backtest/`):  
   Replays historical ticks to simulate strategy performance.

7. **CLI & Orchestration** (`app/`):  
   Offers `collect` and `backtest` commands via Typer, loading settings from YAML.

## Directory Structure

```text
project-root/
├── app/
│   └── main.py
├── collector/
│   └── saxo.py
├── storage/
│   └── store.py
├── aggregator/
│   └── candle_builder.py
├── strategy/
│   ├── indicators.py
│   └── strategies.py
├── executor/
│   ├── order_manager.py
│   └── risk_controller.py
├── backtest/
│   └── replay.py
├── tests/
│   └── test_storage.py
├── config/
│   ├── config.yaml
│   └── loader.py
├── requirements.txt
├── setup.py
├── README.md
└── .github/
    └── workflows/
        └── ci.yml
```

## Getting Started

```bash
pip install -r requirements.txt
forex-bot collect
forex-bot backtest
```
