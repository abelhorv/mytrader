# strategy/strategies.py
import numpy as np
from datetime import timedelta
from .indicators import evaluate_indicators

class BaseStrategy:
    def generate_signal(self, history, tick): ...

class ParametrizedStrategy(BaseStrategy):
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_trade_time = None
        self.last_price = None

    def generate_signal(self,
                        history_1m,
                        tick,
                        candles_5m=None,
                        candles_15m=None):
        prices = [c['close'] for c in history_1m]
        now = tick['timestamp']  
        # Cooldown
        if self.last_trade_time and (now - self.last_trade_time).seconds < self.cfg.cooldown_seconds:
            return "Hold"

        vals = evaluate_indicators(
            prices,
            candles_1m=history_1m,
            candles_5m=candles_5m,
            candles_15m=candles_15m,
            cfg=self.cfg,
        )


        rsi, slope, macd, macd_signal, boll, pattern, c1, c5, c15 = vals
        price = prices[-1]
        sma = np.mean(prices[-self.cfg.sma_period:])

        # Scores
        th = self.cfg.thresholds
        weights = self.cfg.weights
        rsi_score   =  1 if rsi < th.rsi_buy   else -1 if rsi > th.rsi_sell   else 0
        trend_score =  1 if slope > th.slope_buy else -1 if slope < th.slope_sell else 0
        sma_score   =  1 if price > sma else -1 if price < sma else 0
        macd_diff   =  macd - macd_signal
        macd_score  =  1 if macd_diff > self.cfg.macd_tolerance else -1 if macd_diff < -self.cfg.macd_tolerance else 0

        total = (
            rsi_score   * weights.rsi +
            trend_score * weights.trend +
            sma_score   * weights.sma +
            macd_score  * weights.macd +
            boll        * weights.bollinger +
            pattern     * weights.pattern +
            c1          * weights.candle_1m +
            c5          * weights.candle_5m +
            c15         * weights.candle_15m
        )

        # Minimum gap
        if self.last_price and abs(price - self.last_price) < self.cfg.min_trade_gap:
            return "Hold"

        # Decision
        if total > 0.5 + self.cfg.hysteresis_margin:
            action = "Buy"
        elif total < -0.5 - self.cfg.hysteresis_margin:
            action = "Sell"
        else:
            action = "Hold"

        if action in ("Buy", "Sell"):
            self.last_trade_time = now
            self.last_price = price
        return action



