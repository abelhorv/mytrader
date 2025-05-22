# tests/test_candle_patterns_known.py

import pytest
from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
    detect_double_bottom,
    detect_double_top,
)

# --------------------------------------------
# “Golden” candle-pattern cases and expected scores
# --------------------------------------------

# 1) Single-bar patterns: (candle, expected_score, name)
SINGLE_BAR_CASES = [
    (
        {'open': 1.0, 'high': 1.1, 'low': 0.9, 'close': 1.01, 'volume': 50},
        0.5,
        'Doji'
    ),
    (
        {'open': 1.0, 'high': 1.05, 'low': 0.6, 'close': 1.2, 'volume': 60},
        0.4,
        'Hammer'
    ),
    (
        {'open': 1.2, 'high': 1.7, 'low': 1.1, 'close': 1.0, 'volume': 60},
        -0.4,
        'Shooting Star'
    ),
    (
        {'open': 1.0, 'high': 1.6, 'low': 0.95, 'close': 1.7, 'volume': 80},
        0.6,
        'Bullish Engulf'
    ),
    (
        {'open': 1.7, 'high': 1.75, 'low': 1.4, 'close': 1.2, 'volume': 80},
        -0.6,
        'Bearish Engulf'
    ),
    (
        {'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.3, 'volume': 30},
        0.0,
        'Neutral'
    ),
]

# 2) Two-bar engulfing: (prev, curr, expected_score, name)
MULTI_BAR_CASES = [
    (
        {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 40},
        {'open': 1.0, 'high': 1.4, 'low': 1.0, 'close': 1.3, 'volume': 50},
        0.6,
        'Bullish Engulf'
    ),
    (
        {'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.2, 'volume': 40},
        {'open': 1.15, 'high': 1.2, 'low': 0.8, 'close': 0.9, 'volume': 50},
        -0.6,
        'Bearish Engulf'
    ),
    (
        {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 40},
        {'open': 1.1, 'high': 1.15, 'low': 1.05, 'close': 1.12, 'volume': 50},
        0.0,
        'No Engulf'
    ),
]

# 3) Five-bar continuation: (list_of_5_candles, expected_score, name)
FIVE_BAR_CASES = [
    (
        [
            {'open': 1.0, 'high': 2.0, 'low': 1.0, 'close': 1.8, 'volume': 20},
            {'open': 1.8, 'high': 1.85, 'low': 1.7, 'close': 1.7, 'volume': 15},
            {'open': 1.7, 'high': 1.8, 'low': 1.6, 'close': 1.6, 'volume': 15},
            {'open': 1.6, 'high': 1.75, 'low': 1.5, 'close': 1.55, 'volume': 15},
            {'open': 1.55, 'high': 2.1, 'low': 1.55, 'close': 2.0, 'volume': 25},
        ],
        0.9,
        'Rising Three Methods'
    ),
    (
        [
            {'open': 2.0, 'high': 2.0, 'low': 1.5, 'close': 1.6, 'volume': 20},
            {'open': 1.6, 'high': 1.7, 'low': 1.6, 'close': 1.7, 'volume': 15},
            {'open': 1.7, 'high': 1.8, 'low': 1.65, 'close': 1.75, 'volume': 15},
            {'open': 1.75, 'high': 1.85, 'low': 1.7, 'close': 1.8, 'volume': 15},
            {'open': 1.8, 'high': 1.85, 'low': 1.3, 'close': 1.25, 'volume': 25},
        ],
        -0.9,
        'Falling Three Methods'
    ),
    (
        [
            {'open': 1.0, 'high': 1.5, 'low': 1.0, 'close': 1.3, 'volume': 20},
            {'open': 1.3, 'high': 1.4, 'low': 1.2, 'close': 1.25, 'volume': 15},
            {'open': 1.25, 'high': 1.3, 'low': 1.1, 'close': 1.2, 'volume': 15},
            {'open': 1.2, 'high': 1.25, 'low': 1.15, 'close': 1.2, 'volume': 15},
            {'open': 1.2, 'high': 1.35, 'low': 1.2, 'close': 1.3, 'volume': 25},
        ],
        0.0,
        'No Continuation'
    ),
]

# 4) Double bottom & top on price series: (series, func_name, expected_score)
DOUBLE_SERIES_CASES = [
    ([5, 3, 4, 3, 5, 6, 7], 'double_bottom', 0.5),
    ([5, 3, 4, 2.8, 5, 6],         'double_bottom', 0.0),
    ([1, 3, 2, 3, 1, 0, 1],        'double_top',   -0.5),
    ([1, 3, 2, 2.5, 1],            'double_top',    0.0),
]

# --------------------------------------------
# Parametrized tests
# --------------------------------------------

@pytest.mark.parametrize("candle, expected, name", SINGLE_BAR_CASES)
def test_detect_candle_pattern_known(candle, expected, name):
    score = detect_candle_pattern(candle)
    assert score == pytest.approx(expected), f"{name} gave {score}"

@pytest.mark.parametrize("prev, curr, expected, name", MULTI_BAR_CASES)
def test_detect_multi_candle_pattern_known(prev, curr, expected, name):
    score = detect_multi_candle_pattern(prev, curr)
    assert score == pytest.approx(expected), f"{name} gave {score}"

@pytest.mark.parametrize("candles, expected, name", FIVE_BAR_CASES)
def test_detect_five_candle_pattern_known(candles, expected, name):
    score = detect_five_candle_pattern(candles)
    assert score == pytest.approx(expected), f"{name} gave {score}"

@pytest.mark.parametrize("series, func_name, expected", DOUBLE_SERIES_CASES)
def test_detect_double_bottom_top_known(series, func_name, expected):
    if func_name == 'double_bottom':
        score = detect_double_bottom(series, order=1)
    else:
        score = detect_double_top(series,    order=1)
    assert score == pytest.approx(expected), f"{func_name} gave {score}"

