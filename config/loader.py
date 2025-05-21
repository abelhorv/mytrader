# config/loader.py
import os, yaml
from pydantic import BaseModel
from typing import List, Optional, Dict

class CollectorConfig(BaseModel):
    endpoint: str
    symbols: List[str]

class StorageConfig(BaseModel):
    database: str
    db_config: Optional[Dict] = None

class AggregatorConfig(BaseModel):
    intervals: List[int]

class Weights(BaseModel):
    rsi: float
    trend: float
    sma: float
    macd: float
    bollinger: float
    pattern: float
    candle_1m: float
    candle_5m: float
    candle_15m: float

class Thresholds(BaseModel):
    rsi_buy: float
    rsi_sell: float
    slope_buy: float
    slope_sell: float

class StrategyConfig(BaseModel):
    rsi_period:        int
    sma_period:        int
    trend_window:      int
    macd_fast:         int
    macd_slow:         int
    macd_signal:       int
    bollinger_period:  int
    bollinger_std_dev: float
    cooldown_seconds:  int
    min_trade_gap:     float
    hysteresis_margin: float
    macd_tolerance:    float
    weights:           Weights
    thresholds:        Thresholds

class BacktestConfig(BaseModel):
    start: str

class ExecutorConfig(BaseModel):
    slippage: float

class Settings(BaseModel):
    collector: CollectorConfig
    storage:   StorageConfig
    aggregator:AggregatorConfig
    strategy:  StrategyConfig
    backtest:  BacktestConfig
    executor:  ExecutorConfig

def load_config(path: str = "config/config.yaml") -> Settings:
    with open(path) as f:
        data = yaml.safe_load(f)

    # merge in secrets if present
    secret_path = os.path.join(os.path.dirname(path), "db.secret.yaml")
    if os.path.exists(secret_path):
        data.setdefault("storage", {})["db_config"] = yaml.safe_load(open(secret_path))

    return Settings(**data)

