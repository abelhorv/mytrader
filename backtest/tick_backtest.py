#!/usr/bin/env python3
import psycopg2
import yaml
from datetime import datetime, timedelta

from strategy.indicators import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern,
)
from storage.indicators import load_candle_table

# ——— Helpers ———

def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)

def truncate_timestamp(ts, minutes):
    ts = ts.replace(second=0, microsecond=0)
    return ts - timedelta(minutes=ts.minute % minutes)

def fetch_ticks(conn, start, end):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, timestamp, bid, ask, mid, bid_size, ask_size
              FROM pricesandvolume
             WHERE timestamp BETWEEN %s AND %s
             ORDER BY timestamp ASC
        """, (start, end))
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def make_candle_builder(interval):
    """Returns a function that, on each tick, either extends
       or rolls over a candle of `interval` minutes."""
    state = {'bucket': None, 'o': None, 'h': None, 'l': None, 'c': None, 'v': 0}
    def update(ts, price, volume):
        nonlocal state
        b = truncate_timestamp(ts, interval)
        if state['bucket'] is None or b != state['bucket']:
            # start new candle
            state = {
                'bucket': b,
                'o': price, 'h': price, 'l': price, 'c': price,
                'v': volume
            }
        else:
            # extend existing
            state['h'] = max(state['h'], price)
            state['l'] = min(state['l'], price)
            state['c'] = price
            state['v'] += volume
        return state.copy()
    return update

# ——— Main backtest ———

def main():
    # load config
    bc = load_yaml('config/config.yaml')['backtest']
    db = load_yaml('config/db.secret.yaml')
    start = datetime.fromisoformat(bc['start'])
    end   = datetime.fromisoformat(bc['end'])

    # open DB & fetch last 5 completed candles
    conn   = psycopg2.connect(**db)
    past1m  = load_candle_table(conn, "candles_m1",  limit=5)
    past5m  = load_candle_table(conn, "candles_m5",  limit=5)
    past15m = load_candle_table(conn, "candles_m15", limit=5)

    # prepare in-memory builders
    b1   = make_candle_builder(1)
    b5   = make_candle_builder(5)
    b15  = make_candle_builder(15)

    # for rollover detection
    last_bucket = {1: None, 5: None, 15: None}
    last_state  = {1: None, 5: None, 15: None}

    ticks = fetch_ticks(conn, start, end)
    if not ticks:
        print("[ERROR] No ticks in window.")
        return

    for t in ticks:
        ts   = t['timestamp']
        mid  = t['mid']
        vsz  = (t['bid_size'] or 0) + (t['ask_size'] or 0)

        # 1) rollover detection: when the minute/5/15 bucket changes, archive the old bar
        for iv in (1, 5, 15):
            bkt = truncate_timestamp(ts, iv)
            if last_bucket[iv] is not None and bkt != last_bucket[iv]:
                completed = last_state[iv]
                bar = {
                    'timestamp': completed['bucket'],
                    'open':      completed['o'],
                    'high':      completed['h'],
                    'low':       completed['l'],
                    'close':     completed['c'],
                    'volume':    completed['v'],
                }
                if iv == 1:
                    past1m  = (past1m  + [bar])[-5:]
                elif iv == 5:
                    past5m  = (past5m  + [bar])[-5:]
                else:
                    past15m = (past15m + [bar])[-5:]
            last_bucket[iv] = bkt

        # 2) update live candles
        c1   = b1(ts, mid, vsz);  last_state[1]  = c1
        c5   = b5(ts, mid, vsz);  last_state[5]  = c5
        c15  = b15(ts, mid, vsz); last_state[15] = c15

        # 3) normalize to full-bar format
        full_c1 = {
            'timestamp': c1['bucket'],
            'open':      c1['o'],
            'high':      c1['h'],
            'low':       c1['l'],
            'close':     c1['c'],
            'volume':    c1['v'],
        }
        full_c5 = {
            'timestamp': c5['bucket'],
            'open':      c5['o'],
            'high':      c5['h'],
            'low':       c5['l'],
            'close':     c5['c'],
            'volume':    c5['v'],
        }
        full_c15 = {
            'timestamp': c15['bucket'],
            'open':      c15['o'],
            'high':      c15['h'],
            'low':       c15['l'],
            'close':     c15['c'],
            'volume':    c15['v'],
        }

        # 4) build up 5-bar series including the current incomplete candle
        s1  = (past1m[-4:]  if len(past1m)  >= 4 else past1m[:])  + [full_c1]
        s5  = (past5m[-4:]  if len(past5m)  >= 4 else past5m[:])  + [full_c5]
        s15 = (past15m[-4:] if len(past15m) >= 4 else past15m[:]) + [full_c15]

        # 5) run all 3 detectors
        S1  = detect_candle_pattern      (s1[-1])
        E1  = detect_multi_candle_pattern(s1[-2], s1[-1])
        F1  = detect_five_candle_pattern (s1)

        S5  = detect_candle_pattern      (s5[-1])
        E5  = detect_multi_candle_pattern(s5[-2], s5[-1])
        F5  = detect_five_candle_pattern (s5)

        S15 = detect_candle_pattern      (s15[-1])
        E15 = detect_multi_candle_pattern(s15[-2], s15[-1])
        F15 = detect_five_candle_pattern (s15)

        # 6) debug print
        print(
            f"{ts} | Tick={mid:.5f}  sz={vsz}  | "
            f"1m OHLCHV={full_c1['open']:.5f}/{full_c1['high']:.5f}/"
            f"{full_c1['low']:.5f}/{full_c1['close']:.5f}/{full_c1['volume']}  | "
            f"S1={S1:.2f},E1={E1:.2f},F1={F1:.2f}  | "
            f"S5={S5:.2f},E5={E5:.2f},F5={F5:.2f}  | "
            f"S15={S15:.2f},E15={E15:.2f},F15={F15:.2f}"
        )

        # … here you’d hand s1/s5/s15 to evaluate_strategy() …

    conn.close()

if __name__ == '__main__':
    main()

