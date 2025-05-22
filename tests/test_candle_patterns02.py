import pytest

from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
    detect_double_bottom,
    detect_double_top,
)

# -----------------------------
# Toy data for single-bar patterns
# -----------------------------
DOJI_CANDLE = {'open': 1.0, 'high': 1.05, 'low': 0.95, 'close': 1.0, 'volume': 100}
HAMMER_CANDLE = {'open': 1.0, 'high': 1.05, 'low': 0.80, 'close': 1.2, 'volume': 150}
SHOOTING_STAR = {'open': 1.2, 'high': 1.5, 'low': 1.15, 'close': 1.0, 'volume': 150}
ENGULF_BULL = {'open': 1.0, 'high': 1.2, 'low': 0.95, 'close': 1.4, 'volume': 200}
ENGULF_BEAR = {'open': 1.4, 'high': 1.45, 'low': 1.3, 'close': 1.0, 'volume': 200}
NON_PATTERN_CANDLE = {'open': 1.0, 'high': 1.2, 'low': 0.9, 'close': 1.05, 'volume': 50}

# -----------------------------
# Toy data for two-bar patterns
# -----------------------------
PREV_BAR = {'open': 1.2, 'high': 1.3, 'low': 1.1, 'close': 1.1, 'volume': 100}
CURR_BAR_BULL = {'open': 1.05, 'high': 1.4, 'low': 1.05, 'close': 1.3, 'volume': 120}
CURR_BAR_BEAR = {'open': 1.1, 'high': 1.2, 'low': 0.9, 'close': 0.8, 'volume': 120}
NON_ENGULF_BAR = {'open': 1.1, 'high': 1.15, 'low': 1.05, 'close': 1.08, 'volume': 80}

# -----------------------------
# Toy data for five-bar continuation (Three Methods)
# -----------------------------
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
NON_THREE = [
    {'open':1.0,'high':1.5,'low':1.0,'close':1.2,'volume':100},
    {'open':1.2,'high':1.3,'low':1.1,'close':1.25,'volume':80},
    {'open':1.25,'high':1.4,'low':1.2,'close':1.35,'volume':70},
    {'open':1.35,'high':1.45,'low':1.3,'close':1.4,'volume':90},
    {'open':1.4,'high':1.6,'low':1.35,'close':1.55,'volume':110},
]

# -----------------------------
# Parametrize timeframes (pattern functions are timeframe-agnostic)
# -----------------------------
@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_single_candle_patterns_timeframes(timeframe):
    # Positive patterns
    assert detect_candle_pattern(DOJI_CANDLE) == pytest.approx(0.5)
    assert detect_candle_pattern(HAMMER_CANDLE) == pytest.approx(0.4)
    assert detect_candle_pattern(SHOOTING_STAR) == pytest.approx(-0.4)
    assert detect_candle_pattern(ENGULF_BULL) == pytest.approx(0.6)
    assert detect_candle_pattern(ENGULF_BEAR) == pytest.approx(-0.6)
    # Negative / non-pattern
    assert detect_candle_pattern(NON_PATTERN_CANDLE) == pytest.approx(0.0)

@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_two_candle_engulfing_timeframes(timeframe):
    # Bullish and bearish engulfing
    assert detect_multi_candle_pattern(PREV_BAR, CURR_BAR_BULL) == pytest.approx(0.6)
    assert detect_multi_candle_pattern(PREV_BAR, CURR_BAR_BEAR) == pytest.approx(-0.6)
    # Non-engulfing should be zero
    assert detect_multi_candle_pattern(PREV_BAR, NON_ENGULF_BAR) == pytest.approx(0.0)

@pytest.mark.parametrize("timeframe", ["1m", "5m", "15m"])
def test_five_bar_continuation_timeframes(timeframe):
    # Rising and falling three methods
    assert detect_five_candle_pattern(RISING_THREE) == pytest.approx(0.9)
    assert detect_five_candle_pattern(FALLING_THREE) == pytest.approx(-0.9)
    # Non-continuation should be zero
    assert detect_five_candle_pattern(NON_THREE) == pytest.approx(0.0)

# -----------------------------
# Tests for double bottom and double top
# -----------------------------
def test_double_bottom_and_top_patterns():
    # Simple double bottom
    prices_db = [5, 3, 4, 3, 5, 6, 7]  # two equal lows at 3
    assert detect_double_bottom(prices_db, order=1) == pytest.approx(0.5)
    # Simple double top
    prices_dt = [1, 3, 2, 3, 1, 0, 1]  # two equal highs at 3
    assert detect_double_top(prices_dt, order=1) == pytest.approx(-0.5)
    # Too dissimilar lows/highs should not trigger
    prices_db_bad = [5, 3, 4, 2.5, 5, 6, 7]
    assert detect_double_bottom(prices_db_bad, order=1) == pytest.approx(0.0)
    prices_dt_bad = [1, 3, 2, 2.5, 1, 0, 1]
    assert detect_double_top(prices_dt_bad, order=1) == pytest.approx(0.0)

