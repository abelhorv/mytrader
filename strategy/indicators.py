# strategy/indicators.py
import numpy as np
from numba import njit
from scipy.signal import argrelextrema
from concurrent.futures import ThreadPoolExecutor

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
    ema_fast = fast_ema(prices, MACD_FAST)
    ema_slow = fast_ema(prices, MACD_SLOW)
    macd_line = ema_fast - ema_slow
    signal_line = fast_ema(macd_line, MACD_SIGNAL)
    return macd_line[-1], signal_line[-1]

@njit
def fast_bollinger(prices):
    if len(prices) < BOLLINGER_PERIOD:
        return 0
    window = prices[-BOLLINGER_PERIOD:]
    sma = np.mean(window)
    std = np.std(window)
    upper = sma + BOLLINGER_STD_DEV * std
    lower = sma - BOLLINGER_STD_DEV * std
    current = prices[-1]
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
    open_ = float(candle['open'])
    close = float(candle['close'])
    high = float(candle['high'])
    low = float(candle['low'])

    body = abs(close - open_)
    range_ = high - low
    if range_ == 0:
        return 0
    body_ratio = body / range_
    upper_wick = high - max(open_, close)
    lower_wick = min(open_, close) - low

    if body_ratio < 0.1:
        return 0.5  # doji
    if close > open_ and lower_wick > body * 1.5 and upper_wick < body:
        return 0.4  # hammer
    if close < open_ and upper_wick > body * 1.5 and lower_wick < body:
        return -0.4  # shooting star
    if close > open_ and open_ < low + 0.3 * range_ and close > open_ + body:
        return 0.6  # bullish engulfing
    if close < open_ and open_ > high - 0.3 * range_ and close < open_ - body:
        return -0.6  # bearish engulfing
    return 0
    body_ratio = body / range_
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']

    if body_ratio < 0.1:
        return 0.5  # doji
    if candle['close'] > candle['open'] and lower_wick > body * 1.5 and upper_wick < body:
        return 0.4  # hammer
    if candle['close'] < candle['open'] and upper_wick > body * 1.5 and lower_wick < body:
        return -0.4  # shooting star
    if candle['close'] > candle['open'] and candle['open'] < candle['low'] + 0.3 * range_ and candle['close'] > candle['open'] + body:
        return 0.6  # bullish engulfing
    if candle['close'] < candle['open'] and candle['open'] > candle['high'] - 0.3 * range_ and candle['close'] < candle['open'] - body:
        return -0.6  # bearish engulfing
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

