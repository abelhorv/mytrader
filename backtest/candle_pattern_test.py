#!/usr/bin/env python3
# backtest/candle_pattern_report.py
import os
import yaml
import requests
from datetime import datetime, timezone, timedelta
import psycopg2
from analytics.candles import (
    detect_candle_pattern,
    detect_multi_candle_pattern,
    detect_five_candle_pattern
)

SINGLE_LABELS = {
    0.5:  "Doji",
    0.7:  "Marubozu",
    0.4:  "Hammer / Hanging Man",
   -0.4:  "Inverted Hammer / Shooting Star",
   -0.5:  "Doji",
   -0.7:  "Marubozu"
}
MULTI_LABELS = {
     0.6: "Bullish Engulfing",
    -0.6: "Bearish Engulfing",
     0.4: "Bullish Harami / Tweezer Bottom",
    -0.4: "Bearish Harami / Tweezer Top",
     0.5: "Piercing Line",
    -0.5: "Dark Cloud Cover"
}


def load_yaml_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


# load once at module top
cfg = yaml.safe_load(open(os.path.expanduser('~/mytrader/config/config.yaml')))
TOKEN_FILE = os.path.expanduser('~/trader/tok.txt')
API_URL    = 'https://gateway.saxobank.com/sim/openapi/chart/v3/charts'
MAX_COUNT  = 1200000

def _load_token():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"Token file not found: {TOKEN_FILE}")
    tok = open(TOKEN_FILE).read().strip()
    if not tok:
        raise ValueError("Empty token file")
    return tok

def fetch_candles(
    start_time: datetime,
    end_time:   datetime,
    horizon:    int = 1
) -> list[dict]:
    """
    Fetch bars between `start_time` and `end_time` (UTC) at `horizon`-minute resolution.
    Returns list of dicts:
      {
        timestamp: datetime,  # timezone-aware UTC
        open:      float,
        high:      float,
        low:       float,
        close:     float,
        volume:    float|None
      }
    Automatically pages (max 1200 bars/call) and adapts to FX vs non-FX fields.
    """
    token      = _load_token()
    uic        = cfg['uic']
    asset_type = cfg.get('asset_type', 'FxSpot')

    # how many bars we need
    total_bars = int((end_time - start_time).total_seconds() / (60 * horizon))
    remaining  = total_bars
    current    = start_time

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept':        'application/json',
    }

    candles = []
    while remaining > 0:
        cnt = min(remaining, MAX_COUNT)
        params = {
            'Uic':                 uic,
            'AssetType':           asset_type,
            'Horizon':             horizon,
            'Count':               cnt,
            'Mode':                'From',             # page forward
            'Time':                current.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ChartSampleFieldSet': 'LastTraded',       # get Volume & Interest
        }

        r = requests.get(API_URL, params=params, headers=headers)
        r.raise_for_status()
        batch = r.json().get('Data', [])
        if not batch:
            break

        for b in batch:
            # parse the ISO string into a datetime
            ts = datetime.strptime(
                b['Time'],
                '%Y-%m-%dT%H:%M:%S.%fZ'
            ).replace(tzinfo=timezone.utc)

            # for FX you'll get OpenBid/HighBid/etc, for non-FX you'll get Open/High/Low/Close
            open_  = b.get('Open',  b.get('OpenBid'))
            high   = b.get('High',  b.get('HighBid'))
            low    = b.get('Low',   b.get('LowBid'))
            close  = b.get('Close', b.get('CloseBid'))
            volume = b.get('Volume')   # FX will return None

            candles.append({
                'timestamp': ts,
                'open':      open_,
                'high':      high,
                'low':       low,
                'close':     close,
                'volume':    volume,
            })

        # advance to just after the last bar
        last = batch[-1]['Time']
        dt   = datetime.strptime(last, '%Y-%m-%dT%H:%M:%S.%fZ')\
                      .replace(tzinfo=timezone.utc)
        current   = dt + timedelta(minutes=horizon)
        remaining -= len(batch)

    return candles

def main():
    # 1) Load config window & DB
    conf = load_yaml_config('config/config.yaml')['backtest']
    start_time = datetime.fromisoformat(conf['start'])
    end_time   = datetime.fromisoformat(conf['end'])
    db_info = load_yaml_config('config/db.secret.yaml')

    # 2) Fetch 5m candles series
    conn = psycopg2.connect(**db_info)
    #series_5m = fetch_candles(conn, 'candles_m5', start_time, end_time)
    series_5m = fetch_candles( start_time, end_time, horizon=5)
    if not series_5m:
        print("[ERROR] No 5m candles in window")
        conn.close()
        return

    # 3) Iterate
    print("timestamp, S5, S5_label, E5, E5_label, F5")
    for i in range(1, len(series_5m)):
        curr = series_5m[i]
        prev = series_5m[i-1]
        # S5: single on current
        S5 = detect_candle_pattern(curr)
        single_lbl = SINGLE_LABELS.get(S5, '')
        # E5: multi on prev->curr
        E5 = detect_multi_candle_pattern(prev, curr)
        multi_lbl = MULTI_LABELS.get(E5, '')
        # F5: five-candle on rolling window ending at curr
        window = series_5m[max(0, i-4):i+1]
        F5 = detect_five_candle_pattern(window) if len(window)==5 else 0
        # Print
        ts = curr['timestamp'].isoformat()
        print(
        f"{ts}, O={curr['open']:.6f}, H={curr['high']:.6f}, L={curr['low']:.6f}, C={curr['close']:.6f}, V={curr['volume']}, "
        f"S5={S5:+.2f} ({single_lbl}), "
        f"E5={E5:+.2f} ({multi_lbl}), "
        f"F5={F5:+.2f}"
        )

    conn.close()

if __name__ == '__main__':
    main()

