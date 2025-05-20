import yaml
from pydantic import BaseModel
from typing import List

class CollectorConfig(BaseModel):
    endpoint: str
    symbols: List[str]

class StorageConfig(BaseModel):
    database: str

class AggregatorConfig(BaseModel):
    intervals: List[int]

class StrategyConfig(BaseModel):
    rsi_period: int

class BacktestConfig(BaseModel):
    start: str

class ExecutorConfig(BaseModel):
    slippage: float

class Settings(BaseModel):
    collector: CollectorConfig
    storage: StorageConfig
    aggregator: AggregatorConfig
    strategy: StrategyConfig
    backtest: BacktestConfig
    executor: ExecutorConfig

def load_config(path: str = "config/config.yaml") -> Settings:
    with open(path) as f:
        data = yaml.safe_load(f)
    return Settings(**data)
