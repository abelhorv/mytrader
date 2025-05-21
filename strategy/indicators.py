# strategy/indicators.py
import numpy as np
from numba import njit
from scipy.signal import argrelextrema
from concurrent.futures import ThreadPoolExecutor

from config.loader import load_config

# Load strategy parameters from config as module‐level constants
_CFG = load_config().strategy
RSI_PERIOD       = _CFG.rsi_period
SMA_PERIOD       = _CFG.sma_period
TREND_WINDOW     = _CFG.trend_window
MACD_FAST        = _CFG.macd_fast
MACD_SLOW        = _CFG.macd_slow
MACD_SIGNAL      = _CFG.macd_signal
BOLLINGER_PERIOD = _CFG.bollinger_period
BOLLINGER_STD_DEV= _CFG.bollinger_std_dev


# Numba-accelerated primitives
@njit
def fast_rsi(prices, period):
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

@njit
def fast_slope(prices):
    x = np.arange(len(prices))
    x_mean = np.mean(x)
    y_mean = np.mean(prices)
    numerator = np.sum((x - x_mean) * (prices - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    return numerator / denominator if denominator != 0 else 0.0

@njit
def fast_ema(data, span):
    alpha = 2 / (span + 1)
    result = np.empty_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result

@njit
def fast_macd(prices):
     if len(prices) < MACD_SLOW + MACD_SIGNAL:
         return 0.0, 0.0
     ema_fast   = fast_ema(prices, MACD_FAST)
     ema_slow   = fast_ema(prices, MACD_SLOW)
     macd_line  = ema_fast - ema_slow
     signal_line= fast_ema(macd_line, MACD_SIGNAL)
     return macd_line[-1], signal_line[-1]
 
@njit
def fast_bollinger(prices):
    if len(prices) < BOLLINGER_PERIOD:
        return 0
    window = prices[-BOLLINGER_PERIOD:]
    sma    = np.mean(window)
    std    = np.std(window)
    upper  = sma + BOLLINGER_STD_DEV * std
    lower  = sma - BOLLINGER_STD_DEV * std
    current= prices[-1]
    return 1 if current < lower else -1 if current > upper else 0

def detect_double_bottom(prices, order=5, tolerance=0.002):
    if len(prices) < order * 3:
        return 0
    minima = argrelextrema(prices, np.less_equal, order=order)[0]
    if len(minima) < 2:
        return 0
    low1, low2 = prices[minima[-2]], prices[minima[-1]]
    avg = (low1 + low2) / 2
    if abs(low1 - low2) / avg < tolerance:
        mid = prices[(minima[-2] + minima[-1]) // 2]
        if mid > low1 and mid > low2:
            return 0.5
    return 0

def detect_double_top(prices, order=5, tolerance=0.002):
    if len(prices) < order * 3:
        return 0
    maxima = argrelextrema(prices, np.greater_equal, order=order)[0]
    if len(maxima) < 2:
        return 0
    high1, high2 = prices[maxima[-2]], prices[maxima[-1]]
    avg = (high1 + high2) / 2
    if abs(high1 - high2) / avg < tolerance:
        mid = prices[(maxima[-2] + maxima[-1]) // 2]
        if mid < high1 and mid < high2:
            return -0.5
    return 0


def detect_candle_pattern(candle):
    """
    Detects simple single-candle patterns and returns a score:
      +0.5 Doji
      +0.4 Hammer
      -0.4 Shooting Star
      +0.6 “Engulfing-style” bullish
      -0.6 “Engulfing-style” bearish
      0    None / neutral
    """
    o = float(candle['open'])
    c = float(candle['close'])
    h = float(candle['high'])
    l = float(candle['low'])

    body = abs(c - o)
    total_range = h - l
    if total_range == 0:
        return 0

    body_ratio = body / total_range
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Doji: very small body
    if body_ratio < 0.1:
        return 0.5
    # Hammer: green, long lower wick
    if c > o and lower_wick > body * 1.5 and upper_wick < body:
        return 0.4
    # Shooting Star: red, long upper wick
    if c < o and upper_wick > body * 1.5 and lower_wick < body:
        return -0.4
    # “Engulfing-style” bullish: green, opens low in range, closes strongly above
    if c > o and o < l + 0.3 * total_range and c > o + body:
        return 0.6
    # “Engulfing-style” bearish: red, opens high in range, closes strongly below
    if c < o and o > h - 0.3 * total_range and c < o - body:
        return -0.6

    return 0


def detect_multi_candle_pattern(prev, curr):
    """
    True (2-candle) Engulfing:
      +0.6  Bullish engulfing  (current body fully engulfs prior body, and is bullish)
      -0.6  Bearish engulfing  (current body fully engulfs prior body, and is bearish)
      0     otherwise
    """
    o0, c0 = float(prev['open']),  float(prev['close'])
    o1, c1 = float(curr['open']),  float(curr['close'])
    body0 = abs(c0 - o0)
    body1 = abs(c1 - o1)
    # current must have bigger body than prior
    if body1 <= body0:
        return 0
    # bullish engulfing: current green, prior red, and current engulfs prior
    if c1 > o1 and c0 < o0 and o1 < c0 and c1 > o0:
        return 0.6
    # bearish engulfing: current red, prior green, and current engulfs prior
    if c1 < o1 and c0 > o0 and o1 > c0 and c1 < o0:
        return -0.6
    return 0

def detect_five_candle_pattern(candles):
    """
    Five-bar continuation ("Three Methods"):
      +0.9  Rising Three Methods (bullish)
      -0.9  Falling Three Methods (bearish)
      0     otherwise
    Expects `candles` as a list of 5 dicts (oldest first).
    """
    # unpack prices
    o = [float(c['open'])  for c in candles]
    c = [float(c['close']) for c in candles]
    h = [float(c['high'])  for c in candles]
    l = [float(c['low'])   for c in candles]

    def inside(i):
        return h[i] < h[0] and l[i] > l[0]

    # Rising Three Methods
    if (
        c[0] > o[0] and                         # bar0 bullish
        all(c[i] <= o[i] for i in (1,2,3)) and  # bars1–3 bearish/flat
        all(inside(i)     for i in (1,2,3)) and # inside bar0's range
        c[4] > o[4] and                         # bar4 bullish
        c[4] > h[0]                             # closes above bar0.high
    ):
        return 0.9

    # Falling Three Methods
    if (
        c[0] < o[0] and
        all(c[i] >= o[i] for i in (1,2,3)) and
        all(inside(i)     for i in (1,2,3)) and
        c[4] < o[4] and
        c[4] < l[0]
    ):
        return -0.9

    return 0





def evaluate_indicators(
    prices, 
    candles_1m=None, candles_5m=None, candles_15m=None,
    cfg=None
):
    """Returns tuple (rsi, slope, macd, macd_signal, bollinger, pattern, c1, c5, c15)"""
    params = cfg
    prices_np = np.array(prices, dtype=np.float64)

    with ThreadPoolExecutor() as executor:
        futures = {
            'rsi': executor.submit(fast_rsi, prices_np, params.rsi_period),
            'slope': executor.submit(fast_slope, prices_np[-params.trend_window:]),
            'macd': executor.submit(fast_macd, prices_np),
            'boll': executor.submit(fast_bollinger, prices_np),
            'pattern': executor.submit(
                lambda: float(detect_double_bottom(prices_np)) + float(detect_double_top(prices_np))
            ),
        }
        results = {k: f.result() for k, f in futures.items()}
        macd, macd_signal = results['macd']
    # candle scores
    c1 = detect_candle_pattern(candles_1m[-1]) if candles_1m else 0
    c5 = detect_candle_pattern(candles_5m[-1]) if candles_5m else 0
    c15= detect_candle_pattern(candles_15m[-1]) if candles_15m else 0

    return (
        results['rsi'], 
        results['slope'],
        macd,
        macd_signal,
        results['boll'],
        results['pattern'],
        c1,
        c5,
        c15
    )

