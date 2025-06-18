#!/usr/bin/env python3
import os
import sys
import subprocess
import yaml
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# === CONFIG & TOKEN LOADING ===

# Adjust this path as needed
CONFIG_PATH = os.path.expanduser('~/mytrader/config/config.yaml')
TOKEN_FILE  = os.path.expanduser('~/trader/tok.txt')

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def load_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"[FATAL] Token file '{TOKEN_FILE}' not found.")
        sys.exit(1)
    token = open(TOKEN_FILE).read().strip()
    if not token:
        print(f"[FATAL] Token file '{TOKEN_FILE}' is empty.")
        sys.exit(1)
    return token

def refresh_token():
    print("[INFO] Refreshing token…")
    res = subprocess.run(
        ["python3", "refresh_token.py"],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        print("[ERROR] Token refresh failed:", res.stderr)
        return False
    print("[INFO] Token refreshed.")
    return True

cfg   = load_config(CONFIG_PATH)
token = load_token()

uic        = cfg['uic']
asset_type = cfg.get('asset_type', 'FxSpot')
tz_name    = cfg.get('timezone', 'Europe/Zurich')
local_tz   = ZoneInfo(tz_name)

# === COMPUTE UTC WINDOW (unchanged) ===
end_local   = datetime.now(local_tz)
start_local = end_local - timedelta(hours=24)
end_utc     = end_local.astimezone(timezone.utc)
start_utc   = start_local.astimezone(timezone.utc)

total_count = int((end_utc - start_utc).total_seconds() / 60)
MAX_COUNT   = 1200

url     = 'https://gateway.saxobank.com/sim/openapi/chart/v3/charts'
headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

# === FETCH PAGES ===
all_bars, remaining, current_time = [], total_count, end_utc
while remaining > 0:
    cnt = min(remaining, MAX_COUNT)
    params = {
        'Uic':       uic,
        'AssetType': asset_type,
        'Horizon':   1,
        'Count':     cnt,
        'Mode':      'UpTo',
        'Time':      current_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    batch = r.json().get('Data', [])
    if not batch: break
    all_bars = batch + all_bars
    # step back
    earliest = datetime.strptime(batch[-1]['Time'],
                                 '%Y-%m-%dT%H:%M:%S.%fZ'
                                ).replace(tzinfo=timezone.utc)
    current_time = earliest - timedelta(minutes=1)
    remaining   -= cnt

# === CONVERT TO LOCAL TZ & PRINT ===
for bar in all_bars:
    dt_utc = datetime.strptime(bar['Time'], '%Y-%m-%dT%H:%M:%S.%fZ')\
                  .replace(tzinfo=timezone.utc)
    dt_loc = dt_utc.astimezone(local_tz)
    bar['Time'] = dt_loc.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

import json
print(json.dumps(all_bars, indent=2))

