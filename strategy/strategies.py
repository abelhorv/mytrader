# strategy/strategies.py
import numpy as np
from datetime import timedelta
from .indicators import evaluate_indicators

class BaseStrategy:
    def generate_signal(self, history, tick):
        ...

class ParametrizedStrategy(BaseStrategy):
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_trade_time = None
        self.last_price = None

    def generate_signal(self, history_1m, tick, candles_5m=None, candles_15m=None):
        now = tick['timestamp']
        price = tick['price']

        # Cooldown: skip if within cooldown period
        if self.last_trade_time and (now - self.last_trade_time).seconds < self.cfg.cooldown_seconds:
            return "Hold"

        # Evaluate pattern & candle scores
        # evaluate_indicators returns: rsi, slope, macd, macd_signal, boll, pattern, c1, c5, c15
        scores = evaluate_indicators(
            [c['close'] for c in history_1m],
            candles_1m=history_1m,
            candles_5m=candles_5m,
            candles_15m=candles_15m,
            cfg=self.cfg
        )
        # Extract only candle scores
        c1, c5, c15 = scores[6], scores[7], scores[8]

        # Aggregate into a total candle score
        w = self.cfg.weights
        total_score = (
              c1  * w.candle_1m
            + c5  * w.candle_5m
            + c15 * w.candle_15m
        )

        # Enforce minimum price movement gap
        if self.last_price and abs(price - self.last_price) < self.cfg.min_trade_gap:
            return "Hold"

        # Decision thresholds with hysteresis
        upper = 0.5 + self.cfg.hysteresis_margin
        lower = -0.5 - self.cfg.hysteresis_margin
        if total_score > upper:
            action = "Buy"
        elif total_score < lower:
            action = "Sell"
        else:
            action = "Hold"

        # Update last trade if executed
        if action in ("Buy", "Sell"):
            self.last_trade_time = now
            self.last_price = price

        return action

