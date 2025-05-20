from .indicators import rsi

class BaseStrategy:
    def generate_signal(self, history, tick):
        raise NotImplementedError

class RsiStrategy(BaseStrategy):
    def __init__(self, period, overbought=70, oversold=30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def generate_signal(self, history, tick):
        if len(history) < self.period:
            return 'HOLD'
        value = rsi(history, self.period)
        if value > self.overbought:
            return 'SELL'
        if value < self.oversold:
            return 'BUY'
        return 'HOLD'
