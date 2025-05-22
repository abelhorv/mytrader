import pytest

from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
    detect_double_bottom,
    detect_double_top,
)

# --------------------------------------------
# Additional tests for candle indicator logic
# --------------------------------------------

# 1) Single-bar patterns (positive and negative cases)
@pytest.mark.parametrize("candle, expected", [
    # Doji (very small body)
    ({'open': 1.0, 'high': 1.1, 'low': 0.9, 'close': 1.01, 'volume': 50}, 0.5),
    # Hammer (long lower wick > 1.5x body)
    ({'open': 1.0, 'high': 1.05, 'low': 0.6, 'close': 1.2, 'volume': 60}, 0.4),
    # Shooting Star (long upper wick > 1.5x body)
    ({'open': 1.2, 'high': 1.7, 'low': 1.1, 'close': 1.0, 'volume': 60}, -0.4),
    # Bullish "engulfing-style"
    ({'open': 1.0, 'high': 1.6, 'low': 0.95, 'close': 1.7, 'volume': 80}, 0.6),
    # Bearish "engulfing-style"
    ({'open': 1.7, 'high': 1.75, 'low': 1.4, 'close': 1.2, 'volume': 80}, -0.6),
    # No pattern (neutral bar)
    ({'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.3, 'volume': 30}, 0),
])
def test_detect_candle_pattern_additional(candle, expected):
    assert detect_candle_pattern(candle) == pytest.approx(expected)


# 2) Two-bar engulfing patterns
@pytest.mark.parametrize("prev, curr, expected", [
    # Bullish engulfing: current green, larger body, engulfs prior red
    (
        {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 40},
        {'open': 1.0, 'high': 1.4, 'low': 1.0, 'close': 1.3, 'volume': 50},
        0.6
    ),
    # Bearish engulfing: current red, larger body, engulfs prior green
    (
        {'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.2, 'volume': 40},
        {'open': 1.15, 'high': 1.2, 'low': 0.8, 'close': 0.9, 'volume': 50},
        -0.6
    ),
    # No pattern: body not larger
    (
        {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 40},
        {'open': 1.1, 'high': 1.15, 'low': 1.05, 'close': 1.12, 'volume': 50},
        0
    ),
])
def test_detect_multi_candle_pattern_additional(prev, curr, expected):
    assert detect_multi_candle_pattern(prev, curr) == pytest.approx(expected)


# 3) Five-bar continuation (Three Methods)
@pytest.mark.parametrize("candles, expected", [
    # Rising Three Methods (bullish continuation)
    ([
        {'open': 1.0, 'high': 2.0, 'low': 1.0, 'close': 1.8, 'volume': 20},
        {'open': 1.8, 'high': 1.85, 'low': 1.7, 'close': 1.7, 'volume': 15},
        {'open': 1.7, 'high': 1.8, 'low': 1.6, 'close': 1.6, 'volume': 15},
        {'open': 1.6, 'high': 1.75, 'low': 1.5, 'close': 1.55, 'volume': 15},
        {'open': 1.55, 'high': 2.1, 'low': 1.55, 'close': 2.0, 'volume': 25},
    ], 0.9),
    # Falling Three Methods (bearish continuation)
    ([
        {'open': 2.0, 'high': 2.0, 'low': 1.5, 'close': 1.6, 'volume': 20},
        {'open': 1.6, 'high': 1.7, 'low': 1.6, 'close': 1.7, 'volume': 15},
        {'open': 1.7, 'high': 1.8, 'low': 1.65, 'close': 1.75, 'volume': 15},
        {'open': 1.75, 'high': 1.85, 'low': 1.7, 'close': 1.8, 'volume': 15},
        {'open': 1.8, 'high': 1.85, 'low': 1.3, 'close': 1.25, 'volume': 25},
    ], -0.9),
    # No continuation pattern
    ([
        {'open': 1.0, 'high': 1.5, 'low': 1.0, 'close': 1.3, 'volume': 20},
        {'open': 1.3, 'high': 1.4, 'low': 1.2, 'close': 1.25, 'volume': 15},
        {'open': 1.25, 'high': 1.3, 'low': 1.1, 'close': 1.2, 'volume': 15},
        {'open': 1.2, 'high': 1.25, 'low': 1.15, 'close': 1.2, 'volume': 15},
        {'open': 1.2, 'high': 1.35, 'low': 1.2, 'close': 1.3, 'volume': 25},
    ], 0),
])
def test_detect_five_candle_pattern_additional(candles, expected):
    assert detect_five_candle_pattern(candles) == pytest.approx(expected)


# 4) Double Bottom & Double Top on price series
@pytest.mark.parametrize("series, func, expected", [
    # Simple double bottom
    ([5, 3, 4, 3, 5, 6, 7], detect_double_bottom, 0.5),
    # No double bottom when lows differ too much
    ([5, 3, 4, 2.8, 5, 6], detect_double_bottom, 0),
    # Simple double top
    ([1, 3, 2, 3, 1, 0, 1], detect_double_top, -0.5),
    # No double top when highs unequal
    ([1, 3, 2, 2.5, 1], detect_double_top, 0),
])
def test_detect_double_bottom_top_additional(series, func, expected):
    assert func(series, order=1) == pytest.approx(expected)

