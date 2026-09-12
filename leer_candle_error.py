import os, duckdb
BASE = "/home/mamba/vertical-exploration/delta"
tbl = os.path.join(BASE, "bronze_backtest_vertical_pm")
con = duckdb.connect()
rows = con.execute(
    "SELECT titulo, n_candles, candle_error FROM delta_scan('%s') WHERE n_candles < 0 LIMIT 8" % tbl
).fetchall()
for t,n,err in rows:
    print(t[:50], "| ncandles=", n, "| err=", (err or "")[:150])
