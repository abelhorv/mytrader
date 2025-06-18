# backtest/tick_backtest.py

"""
Backtest script for tick-level trading strategy. Converts ticks into
multi-timeframe candles using the aggregator, then evaluates pattern
signals on the fly.
"""

import psycopg2
import yaml
from datetime import datetime

from storage.indicators import load_candle_table
from aggregator.candles import process_tick, truncate_timestamp
from strategy.indicators import detect_five_candle_pattern


def load_yaml_config(path):
    """Load a YAML file and return its contents as a dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_ticks(connection, start_time, end_time):
    """
    Retrieve tick data between start_time and end_time from the database.
    Returns a list of dict rows with keys: id, timestamp, bid, ask, mid,
    bid_size, ask_size.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, timestamp, bid, ask, mid, bid_size, ask_size
              FROM pricesandvolume
             WHERE timestamp BETWEEN %s AND %s
             ORDER BY timestamp ASC
            """,
            (start_time, end_time)
        )
        columns = [col.name for col in cur.description]
        rows = cur.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def make_candle_builder(interval_minutes):
    """
    Returns a closure that accumulates ticks into an OHLCV candle for
    the given interval (in minutes). Each call returns a copy of the
    current candle state dict.
    """
    state = {'bucket': None, 'o': None, 'h': None, 'l': None, 'c': None, 'v': 0}

    def update_candle(timestamp, price, volume):
        bucket_start = truncate_timestamp(timestamp, interval_minutes)
        if state['bucket'] is None or bucket_start != state['bucket']:
            # initialize a new candle
            state.update({
                'bucket': bucket_start,
                'o': price, 'h': price, 'l': price, 'c': price, 'v': volume
            })
        else:
            # update existing candle
            state['h'] = max(state['h'], price)
            state['l'] = min(state['l'], price)
            state['c'] = price
            state['v'] += volume
        return state.copy()

    return update_candle


def main():
    # Load configuration
    config = load_yaml_config('config/config.yaml')['backtest']
    db_conn_info = load_yaml_config('config/db.secret.yaml')
    start_time = datetime.fromisoformat(config['start'])
    end_time = datetime.fromisoformat(config['end'])

    # Connect to Postgres and load last 5 completed candles
    conn = psycopg2.connect(**db_conn_info)
    recent_1m_candles  = load_candle_table(conn, "candles_m1",  limit=5)
    recent_5m_candles  = load_candle_table(conn, "candles_m5",  limit=5)
    recent_15m_candles = load_candle_table(conn, "candles_m15", limit=5)

    # Prepare in-memory candle builders
    builder_1m  = make_candle_builder(1)
    builder_5m  = make_candle_builder(5)
    builder_15m = make_candle_builder(15)

    # Track previous bucket and live state for rollover detection
    last_bucket_by_interval      = {1: None, 5: None, 15: None}
    last_state_by_interval       = {1: None, 5: None, 15: None}

    # Fetch ticks from the database
    ticks = fetch_ticks(conn, start_time, end_time)
    if not ticks:
        print("[ERROR] No ticks found in the specified window.")
        return

    # Process each tick
    for tick in ticks:
        timestamp = tick['timestamp']
        mid_price = tick['mid']
        # Sum bid_size + ask_size for total tick volume
        tick_volume = (tick['bid_size'] or 0) + (tick['ask_size'] or 0)

        # Delegate all candle aggregation & pattern logic
        result = process_tick(
            timestamp, mid_price, tick_volume,
            recent_1m_candles, recent_5m_candles, recent_15m_candles,
            last_bucket_by_interval, last_state_by_interval,
            builder_1m, builder_5m, builder_15m
        )

        # Unpack updated state
        recent_1m_candles  = result['recent_1m']
        recent_5m_candles  = result['recent_5m']
        recent_15m_candles = result['recent_15m']
        last_bucket_by_interval = result['last_buckets']
        last_state_by_interval  = result['last_states']

        # Extract pattern scores
        scores = result['pattern_scores']
        S1, E1, F1 = scores['S1'], scores['E1'], scores['F1']
        S5, E5, F5 = scores['S5'], scores['E5'], scores['F5']
        S15, E15, F15 = scores['S15'], scores['E15'], scores['F15']

        # Debug print current 1m candle plus scores

        SINGLE_LABELS = {0.5:  "Doji", 0.7:  "Marubozu", 0.4:  "Hammer / Hanging Man", -0.4:  "Inverted Hammer / Shooting Star", -0.5:  "Doji", -0.7:  "Marubozu"}
        MULTI_LABELS = { 0.6: "Bullish Engulfing", -0.6: "Bearish Engulfing", 0.4: "Bullish Harami / Tweezer Bottom", -0.4: "Bearish Harami / Tweezer Top", 0.5: "Piercing Line", -0.5: "Dark Cloud Cover"}

        single = SINGLE_LABELS.get(S5, None)
        multi  = MULTI_LABELS.get(E5, None)
        live_1m = result['candle_states']['1m']
        print(
            f"{timestamp} | Mid={mid_price:.5f} Vol={tick_volume} | "
            f"1m OHLCHV={live_1m['o']:.5f}/{live_1m['h']:.5f}/"
            f"{live_1m['l']:.5f}/{live_1m['c']:.5f}/{live_1m['v']} | "
            f"S5={S5:.2f} shape={single},E5={E5:.2f} shape={multi},F5={F5:.2f} | "
        )

#        print(
#            f"{timestamp} | Mid={mid_price:.5f} Vol={tick_volume} | "
#            f"1m OHLCHV={live_1m['o']:.5f}/{live_1m['h']:.5f}/"
#            f"{live_1m['l']:.5f}/{live_1m['c']:.5f}/{live_1m['v']} | "
#            f"S1={S1:.2f},E1={E1:.2f},F1={F1:.2f} | "
#            f"S5={S5:.2f},E5={E5:.2f},F5={F5:.2f} | "
#            f"S15={S15:.2f},E15={E15:.2f},F15={F15:.2f}"
#        )

    conn.close()

if __name__ == '__main__':
    main()

