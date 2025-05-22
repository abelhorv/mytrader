# aggregator/candles.py

"""
This module handles converting tick data into OHLCV candles for different timeframes (1, 5, 15 minutes),
and detecting standard candle patterns on those aggregated bars.
"""

from datetime import timedelta
from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
)


def truncate_timestamp(timestamp, interval_minutes):
    """
    Truncate a datetime to the start of its interval bucket.
    E.g., for 5-minute intervals, 12:07 -> 12:05.
    """
    timestamp = timestamp.replace(second=0, microsecond=0)
    minutes = timestamp.minute - (timestamp.minute % interval_minutes)
    return timestamp.replace(minute=minutes)


def build_candle_series(recent_candles, current_candle_state):
    """
    Build a list of up to 5 candles: the last 4 completed + the current in-progress candle.
    recent_candles: list of completed candle dicts
    current_candle_state: dict with keys 'bucket','o','h','l','c','v'
    """
    # Keep at most 4 completed candles
    last_completed = recent_candles[-4:] if len(recent_candles) >= 4 else recent_candles[:]
    # Build the current candle dict
    current = {
        'timestamp': current_candle_state['bucket'],
        'open': current_candle_state['o'],
        'high': current_candle_state['h'],
        'low': current_candle_state['l'],
        'close': current_candle_state['c'],
        'volume': current_candle_state['v'],
    }
    return last_completed + [current]


def process_tick(
    timestamp, mid_price, tick_volume,
    recent_candles_1m, recent_candles_5m, recent_candles_15m,
    last_bucket_by_interval, last_candle_state_by_interval,
    builder_1m, builder_5m, builder_15m
):
    """
    Process a single tick:
      1) Detect bucket rollovers for 1, 5, 15 minute candles, and archive completed candles.
      2) Update the in-progress candle for each interval.
      3) Construct a 5-candle series (4 completed + current) for pattern detection.
      4) Run single-, multi-, and five-candle pattern detectors.
    Returns updated recent_candles lists, state dicts, and a dict of pattern scores.
    """
    # 1) Handle end-of-bucket rollover for each interval
    for interval in (1, 5, 15):
        bucket_start = truncate_timestamp(timestamp, interval)
        previous_bucket = last_bucket_by_interval[interval]
        # If we've moved into a new bucket, archive the old candle
        if previous_bucket is not None and bucket_start != previous_bucket:
            completed_state = last_candle_state_by_interval[interval]
            archived_candle = {
                'timestamp': completed_state['bucket'],
                'open': completed_state['o'],
                'high': completed_state['h'],
                'low': completed_state['l'],
                'close': completed_state['c'],
                'volume': completed_state['v'],
            }
            # Append and trim to last 5
            if interval == 1:
                recent_candles_1m.append(archived_candle)
                recent_candles_1m = recent_candles_1m[-5:]
            elif interval == 5:
                recent_candles_5m.append(archived_candle)
                recent_candles_5m = recent_candles_5m[-5:]
            else:
                recent_candles_15m.append(archived_candle)
                recent_candles_15m = recent_candles_15m[-5:]
        # Update last seen bucket
        last_bucket_by_interval[interval] = bucket_start

    # 2) Update in-progress candles
    state_1m = builder_1m(timestamp, mid_price, tick_volume)
    last_candle_state_by_interval[1] = state_1m
    state_5m = builder_5m(timestamp, mid_price, tick_volume)
    last_candle_state_by_interval[5] = state_5m
    state_15m = builder_15m(timestamp, mid_price, tick_volume)
    last_candle_state_by_interval[15] = state_15m

    # 3) Build 5-candle series for pattern detection
    series_1m = build_candle_series(recent_candles_1m, state_1m)
    series_5m = build_candle_series(recent_candles_5m, state_5m)
    series_15m = build_candle_series(recent_candles_15m, state_15m)

    # 4) Run pattern detection
    S1 = detect_candle_pattern(series_1m[-1])
    E1 = detect_multi_candle_pattern(series_1m[-2], series_1m[-1])
    F1 = detect_five_candle_pattern(series_1m)
    S5 = detect_candle_pattern(series_5m[-1])
    E5 = detect_multi_candle_pattern(series_5m[-2], series_5m[-1])
    F5 = detect_five_candle_pattern(series_5m)
    S15 = detect_candle_pattern(series_15m[-1])
    E15 = detect_multi_candle_pattern(series_15m[-2], series_15m[-1])
    F15 = detect_five_candle_pattern(series_15m)

    return {
        'recent_1m': recent_candles_1m,
        'recent_5m': recent_candles_5m,
        'recent_15m': recent_candles_15m,
        'last_buckets': last_bucket_by_interval,
        'last_states': last_candle_state_by_interval,
        'candle_states': {
            '1m': state_1m,
            '5m': state_5m,
            '15m': state_15m,
        },
        'pattern_scores': {
            'S1': S1, 'E1': E1, 'F1': F1,
            'S5': S5, 'E5': E5, 'F5': F5,
            'S15': S15, 'E15': E15, 'F15': F15,
        }
    }
