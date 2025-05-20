import numpy as np

def rsi(candles, period=14):
    closes = [c['close'] for c in candles]
    deltas = np.diff(closes)
    ups = np.where(deltas>0, deltas, 0)
    downs = np.where(deltas<0, -deltas, 0)
    roll_up = np.mean(ups[-period:])
    roll_down = np.mean(downs[-period:])
    rs = roll_up / (roll_down + 1e-6)
    return 100 - (100 / (1 + rs))
