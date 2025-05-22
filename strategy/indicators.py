# strategy/indicators.py
import numpy as np
from numba import njit
from scipy.signal import argrelextrema
from concurrent.futures import ThreadPoolExecutor
from config.loader import load_config

# Load strategy parameters from config as module-level constants
_CFG = load_config().strategy
RSI_PERIOD        = _CFG.rsi_period
SMA_PERIOD        = _CFG.sma_period
TREND_WINDOW      = _CFG.trend_window
MACD_FAST         = _CFG.macd_fast
MACD_SLOW         = _CFG.macd_slow
MACD_SIGNAL       = _CFG.macd_signal
BOLLINGER_PERIOD  = _CFG.bollinger_period
BOLLINGER_STD_DEV = _CFG.bollinger_std_dev

# ------------------- Numba-accelerated primitives -------------------
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

# -------------------- Pattern detection functions --------------------
def detect_double_bottom(prices, order=5, tolerance=0.002):
    arr = np.asarray(prices, float)
    if len(arr) < order * 3:
        return 0
    minima = argrelextrema(arr, np.less_equal, order=order)[0]
    valid = [i for i in minima if order <= i <= len(arr)-1-order]
    if len(valid) < 2:
        return 0
    i1, i2 = valid[-2], valid[-1]
    low1, low2 = arr[i1], arr[i2]
    avg = (low1 + low2) / 2
    if abs(low1 - low2) / avg < tolerance:
        mid_val = arr[(i1 + i2)//2]
        if mid_val > low1 and mid_val > low2:
            return 0.5
    return 0


def detect_double_top(prices, order=5, tolerance=0.002):
    arr = np.asarray(prices, float)
    if len(arr) < order * 3:
        return 0
    maxima = argrelextrema(arr, np.greater_equal, order=order)[0]
    valid = [i for i in maxima if order <= i <= len(arr)-1-order]
    if len(valid) < 2:
        return 0
    i1, i2 = valid[-2], valid[-1]
    hi1, hi2 = arr[i1], arr[i2]
    avg = (hi1 + hi2) / 2
    if abs(hi1 - hi2) / avg < tolerance:
        mid_val = arr[(i1 + i2)//2]
        if mid_val < hi1 and mid_val < hi2:
            return -0.5
    return 0


def detect_candle_pattern(candle):
    o = float(candle['open'])
    c = float(candle['close'])
    h = float(candle['high'])
    l = float(candle['low'])
    body = abs(c - o)
    total = h - l
    if total == 0:
        return 0
    upper = max(0, h - max(o, c))
    lower = max(0, min(o, c) - l)
    ratio = body / total
    # Doji
    if ratio < 0.1:
        return 0.5
    # Hammer
    if c > o and lower >= body and upper <= body:
        return 0.4
    # Shooting Star
    if c < o and upper >= 1.5 * body and lower <= body:
        return -0.4
    # Bullish engulfing-style
    if c > o and o < l + 0.3 * total and c >= o + body:
        return 0.6
    # Bearish engulfing-style
    if c < o and c <= o - body and o > h - 0.4 * total:
        return -0.6
    return 0


def detect_multi_candle_pattern(prev, curr):
    o0, c0 = float(prev['open']), float(prev['close'])
    o1, c1 = float(curr['open']), float(curr['close'])
    body0, body1 = abs(c0 - o0), abs(c1 - o1)
    # require larger body
    if body1 <= body0:
        return 0
    # direction
    return 0.6 if c1 > o1 else -0.6 if c1 < o1 else 0


def detect_five_candle_pattern(candles):
    if len(candles) != 5:
        return 0
    o = [float(c['open']) for c in candles]
    c = [float(c['close']) for c in candles]
    # Rising Three Methods: first and last bullish and middle three bearish/flat
    if c[0] > o[0] and c[4] > o[4] and c[4] > c[0] and all(c[i] <= o[i] for i in range(1,4)):
        return 0.9
    # Falling Three Methods: first and last bearish and middle three bullish/flat
    if c[0] < o[0] and c[4] < o[4] and c[4] < c[0] and all(c[i] >= o[i] for i in range(1,4)):
        return -0.9
    return 0


def evaluate_indicators(prices, candles_1m=None, candles_5m=None, candles_15m=None, cfg=None):
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
    macd_line, macd_signal = results['macd']
    c1  = detect_candle_pattern(candles_1m[-1])  if candles_1m  else 0
    c5  = detect_candle_pattern(candles_5m[-1])  if candles_5m  else 0
    c15 = detect_candle_pattern(candles_15m[-1]) if candles_15m else 0
    return (
        results['rsi'],
        results['slope'],
        macd_line,
        macd_signal,
        results['boll'],
        results['pattern'],
        c1,
        c5,
        c15
    )

