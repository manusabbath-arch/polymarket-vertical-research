import os, duckdb
BASE = "/home/mamba/vertical-exploration/delta"
SNAP = os.path.join(BASE, "forward_snapshots")
con = duckdb.connect()
rows = con.execute("""
  SELECT question, best_bid, best_ask, error, ROUND(profundidad,0) dep
  FROM delta_scan('%s')
  ORDER BY profundidad DESC NULLS LAST
""" % SNAP).fetchall()
n_ok = 0
n_err = 0
for q, bid, ask, err, dep in rows:
    if err:
        n_err += 1
        print("  ERR %-15s :: %s" % (err[:25], (q or "")[:50]))
    else:
        n_ok += 1
        print("  OK  bid=%s ask=%s dep=%8.0f :: %s" % (bid, ask, dep or 0, (q or "")[:45]))
print("\nCon book real: %s | con error: %s | total: %s" % (n_ok, n_err, len(rows)))
