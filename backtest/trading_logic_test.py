import psycopg2
import numpy as np
from datetime import datetime, timedelta
from config.loader import load_config
from strategy.indicators import evaluate_indicators
from strategy.strategies import ParametrizedStrategy

# Load secrets + strategy config
settings  = load_config()
DB_CFG    = settings.storage.db_config
strat_cfg = settings.strategy

# === Trade Control Parameters ===
MIN_PROFIT_PIPS  = strat_cfg.min_profit_pips
MIN_HOLD_SECONDS = strat_cfg.min_hold_seconds

def load_candle_table(table):
    with psycopg2.connect(**DB_CFG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT timestamp, open, high, low, close, volume
                FROM {table}
                ORDER BY timestamp ASC
            """)
            return [
                {
                    "time":   row[0],
                    "open":   float(row[1]),
                    "high":   float(row[2]),
                    "low":    float(row[3]),
                    "close":  float(row[4]),
                    "volume": float(row[5])
                }
                for row in cur.fetchall()
            ]

def backtest():
    candles_1m  = load_candle_table("candles_m1")
    candles_5m  = load_candle_table("candles_m5")
    candles_15m = load_candle_table("candles_m15")

    if not candles_1m:
        print("[ERROR] No 1-minute candles found.")
        return

    prices     = [c["close"] for c in candles_1m]
    volumes    = [c["volume"] for c in candles_1m]
    timestamps = [c["time"]   for c in candles_1m]

    position        = None
    pnl             = 0
    last_trade_time = None
    last_price      = None
    trade_logs      = []
    win_trades      = loss_trades = total_trades = total_hold_time = 0

    strategy = ParametrizedStrategy(strat_cfg)

    for i in range(len(prices)):
        now   = timestamps[i]
        price = prices[i]

        price_buf = prices[:i+1]
        vol_buf   = volumes[:i+1]
        c1m_buf   = candles_1m[:i+1]
        c5m_buf   = [c for c in candles_5m  if c["time"]  <= now]
        c15m_buf  = [c for c in candles_15m if c["time"] <= now]

        vals   = evaluate_indicators(
            price_buf,
            candles_1m  = c1m_buf,
            candles_5m  = c5m_buf,
            candles_15m = c15m_buf,
            cfg         = strat_cfg
        )
        action = strategy.generate_signal(
            history = c1m_buf,
            tick    = {"timestamp": now, "bid": price, "ask": price, "volume": vol_buf[-1]}
        )

        # OPEN
        if position is None and action in ["Buy","Sell"]:
            position        = (action, price)
            last_price      = price
            last_trade_time = now
            trade_logs.append((now,"OPEN",action.upper(),price,None,*vals))
            print(f"{now} OPEN {action} @ {price:.5f}")

        # CLOSE (and possibly re-open)
        elif position is not None:
            pos_type, entry = position
            price_diff      = abs(price - entry)
            held            = (now - last_trade_time).total_seconds()

            if ((pos_type=="Buy"  and action=="Sell") or
                (pos_type=="Sell" and action=="Buy")) \
                and price_diff >= MIN_PROFIT_PIPS \
                and held       >= MIN_HOLD_SECONDS:

                # close
                delta     = (price - entry) if pos_type=="Buy" else (entry - price)
                trade_pnl = delta * 100000
                pnl      += trade_pnl
                total_trades   += 1
                total_hold_time+= held
                win_trades     += int(trade_pnl>0)
                loss_trades    += int(trade_pnl<=0)

                trade_logs.append((now,"CLOSE",action.upper(),price,trade_pnl,*vals))
                print(f"{now} CLOSE {action} @ {price:.5f} PnL={trade_pnl:.2f}")

                # re-open if flip
                if action in ["Buy","Sell"]:
                    position        = (action, price)
                    last_trade_time = now
                    last_price      = price
                    trade_logs.append((now,"OPEN",action.upper(),price,None,*vals))
                    print(f"{now} OPEN {action} @ {price:.5f}")

    # write to trade_signals
    with psycopg2.connect(**DB_CFG) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trade_signals")
            cur.executemany(
                """
                INSERT INTO trade_signals (
                    timestamp, action, signal, price, pnl,
                    rsi, slope, macd, macd_signal, boll, pattern,
                    candle_1m, candle_5m, candle_15m
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                trade_logs
            )

    # summary
    print("\n=== BACKTEST COMPLETE ===")
    print(f"Total PnL: {pnl:.2f}")
    print(f"Trades: {total_trades} (Wins: {win_trades}, Losses: {loss_trades})")
    if total_trades:
        print(f"Win Rate: {100*win_trades/total_trades:.1f}%")
        print(f"Avg Hold Time: {total_hold_time/total_trades:.1f}s")

if __name__ == "__main__":
    backtest()

