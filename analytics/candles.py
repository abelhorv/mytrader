import numpy as np
from numba import njit
from scipy.signal import argrelextrema
from concurrent.futures import ThreadPoolExecutor
from config.loader import load_config


def detect_candle_pattern(candle):
    """
    Detect single-candle formations and return a score:
      - Doji (±0.5)
      - Hammer (0.4) / Hanging Man (-0.4)
      - Inverted Hammer (0.4) / Shooting Star (-0.4)
      - Bullish Marubozu (0.7)
      - Bearish Marubozu (-0.7)
    """
    o = float(candle['open'])
    c = float(candle['close'])
    h = float(candle['high'])
    l = float(candle['low'])
    body = abs(c - o)
    total = h - l
    if total == 0:
        return 0
    upper = h - max(o, c)
    lower = min(o, c) - l
    ratio = body / total

    # Doji: very small body
    if ratio < 0.1:
        return 0.5 if c > o else -0.5 if c < o else 0

    # Marubozu: body covers ~90% of range
    if body >= 0.9 * total:
        return 0.7 if c > o else -0.7

    # Hammer / Hanging Man: long lower wick
    if lower >= 2 * body and upper <= 0.3 * body:
        return 0.4 if c > o else -0.4

    # Inverted Hammer / Shooting Star: long upper wick
    if upper >= 2 * body and lower <= 0.3 * body:
        return 0.4 if c > o else -0.4

    return 0

def detect_multi_candle_pattern(prev, curr):
    """
    Detect two-candle patterns and return a score:
      - Bullish Engulfing (+0.6)
      - Bearish Engulfing (-0.6)
      - Bullish Harami (+0.4)
      - Bearish Harami (-0.4)
      - Piercing Line (+0.5)
      - Dark Cloud Cover (-0.5)
      - Tweezer Bottom (+0.4)
      - Tweezer Top (-0.4)
    """
    # Parse OHLC
    o0, h0, l0, c0 = (float(prev[k]) for k in ('open', 'high', 'low', 'close'))
    o1, h1, l1, c1 = (float(curr[k]) for k in ('open', 'high', 'low', 'close'))
    body0 = abs(c0 - o0)
    body1 = abs(c1 - o1)
    if body1 == 0 or body0 == 0:
        return 0

    # 1. Engulfing (requires larger body)
    if body1 > body0:
        # Bullish Engulfing: curr opens below prev close and closes above prev open
        if c1 > o1 and o1 < c0 and c1 > o0:
            return 0.6
        # Bearish Engulfing: curr opens above prev close and closes below prev open
        if c1 < o1 and o1 > c0 and c1 < o0:
            return -0.6

    # 2. Harami (small body inside prior body)
    # Bullish Harami: prev bearish, curr bullish, curr range within prev body
    if c0 < o0 and c1 > o1 and o1 > c0 and c1 < o0:
        return 0.4
    # Bearish Harami: prev bullish, curr bearish, curr range within prev body
    if c0 > o0 and c1 < o1 and o1 < c0 and c1 > o0:
        return -0.4

    # 3. Piercing Line: prev bearish, curr bullish, opens below prev low, closes above prev midpoint
    midpoint0 = (o0 + c0) / 2
    if c0 < o0 and c1 > o1 and o1 < l0 and c1 > midpoint0:
        return 0.5

    # 4. Dark Cloud Cover: prev bullish, curr bearish, opens above prev high, closes below prev midpoint
    if c0 > o0 and c1 < o1 and o1 > h0 and c1 < (o0 + c0) / 2:
        return -0.5

    # 5. Tweezer Bottom: lows nearly equal, prev bearish, curr bullish
    if abs(l0 - l1) <= 0.01 * (h0 - l0) and c0 < o0 and c1 > o1:
        return 0.4

    # 6. Tweezer Top: highs nearly equal, prev bullish, curr bearish
    if abs(h0 - h1) <= 0.01 * (h0 - l0) and c0 > o0 and c1 < o1:
        return -0.4

    return 0


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



