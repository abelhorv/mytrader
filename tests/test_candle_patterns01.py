import pytest

from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
)

# -----------------------------
# Toy data for pattern tests
# -----------------------------
# Single-bar patterns
DOJI_CANDLE = {'open': 1.0, 'high': 1.05, 'low': 0.95, 'close': 1.0, 'volume': 100}
HAMMER_CANDLE = {'open': 1.0, 'high': 1.05, 'low': 0.80, 'close': 1.2, 'volume': 150}
SHOOTING_STAR = {'open': 1.2, 'high': 1.5, 'low': 1.15, 'close': 1.0, 'volume': 150}
ENGULF_BULL = {'open': 1.0, 'high': 1.2, 'low': 0.95, 'close': 1.4, 'volume': 200}
ENGULF_BEAR = {'open': 1.4, 'high': 1.45, 'low': 1.3, 'close': 1.0, 'volume': 200}

# Two-bar patterns
PREV_BAR = {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 100}
CURR_BAR_BULL = {'open': 1.05, 'high': 1.4, 'low': 1.05, 'close': 1.3, 'volume': 120}
CURR_BAR_BEAR = {'open': 1.1, 'high': 1.2, 'low': 0.9, 'close': 0.8, 'volume': 120}

# Five-bar continuation (Three Methods)
RISING_THREE = [
    {'open':1.0,'high':2.0,'low':1.0,'close':1.8,'volume':100},
    {'open':1.8,'high':2.2,'low':1.7,'close':1.7,'volume':80},
    {'open':1.7,'high':1.9,'low':1.6,'close':1.6,'volume':70},
    {'open':1.6,'high':1.85,'low':1.5,'close':1.55,'volume':90},
    {'open':1.55,'high':2.1,'low':1.55,'close':2.05,'volume':110},
]

FALLING_THREE = [
    {'open':2.0,'high':2.0,'low':1.5,'close':1.6,'volume':100},
    {'open':1.6,'high':1.7,'low':1.6,'close':1.7,'volume':80},
    {'open':1.7,'high':1.8,'low':1.65,'close':1.75,'volume':70},
    {'open':1.75,'high':1.85,'low':1.7,'close':1.8,'volume':90},
    {'open':1.8,'high':1.85,'low':1.3,'close':1.25,'volume':110},
]

# Parametrize timeframes (pattern functions are timeframe-agnostic)
@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_single_candle_patterns_timeframes(timeframe):
    # Doji
    assert detect_candle_pattern(DOJI_CANDLE) == pytest.approx(0.5)
    # Hammer
    assert detect_candle_pattern(HAMMER_CANDLE) == pytest.approx(0.4)
    # Shooting Star
    assert detect_candle_pattern(SHOOTING_STAR) == pytest.approx(-0.4)
    # Bullish Engulfing
    assert detect_candle_pattern(ENGULF_BULL) == pytest.approx(0.6)
    # Bearish Engulfing
    assert detect_candle_pattern(ENGULF_BEAR) == pytest.approx(-0.6)

@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_two_candle_engulfing_timeframes(timeframe):
    # Bullish two-bar engulfing
    assert detect_multi_candle_pattern(PREV_BAR, CURR_BAR_BULL) == pytest.approx(0.6)
    # Bearish two-bar engulfing
    assert detect_multi_candle_pattern(PREV_BAR, CURR_BAR_BEAR) == pytest.approx(-0.6)

@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_five_bar_continuation_timeframes(timeframe):
    # Rising Three Methods bullish
    assert detect_five_candle_pattern(RISING_THREE) == pytest.approx(0.9)
    # Falling Three Methods bearish
    assert detect_five_candle_pattern(FALLING_THREE) == pytest.approx(-0.9)
