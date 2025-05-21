import psycopg2
import yaml
from datetime import datetime, timedelta

# Load configs
#def load_yaml(path):
#    with open(path) as f:
#        return yaml.safe_load(f)
#
#db_cfg = load_yaml('config/db.secret.yaml')

def load_candle_table(conn, table, limit=None):
    """
    Fetch the most recent `limit` rows from `table`;
    if limit is None, fetch all.
    Returns list of dicts sorted ascending by timestamp.
    """
#    with psycopg2.connect(**db_cfg) as conn:
    with conn.cursor() as cur:
         if limit:
             cur.execute(f"""
                 SELECT timestamp, open, high, low, close, volume
                   FROM {table}
               ORDER BY timestamp DESC
                  LIMIT %s
             """, (limit,))
             rows = cur.fetchall()
             rows.reverse()   # now oldest → newest
         else:
             cur.execute(f"""
                 SELECT timestamp, open, high, low, close, volume
                   FROM {table}
               ORDER BY timestamp ASC
             """)
             rows = cur.fetchall()

         return [
             {
                 "time": row[0],
                 "open": float(row[1]),
                 "high": float(row[2]),
                 "low":  float(row[3]),
                 "close":float(row[4]),
                 "volume": float(row[5])
             }
             for row in rows
         ]

