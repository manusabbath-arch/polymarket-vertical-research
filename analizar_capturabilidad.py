import os
import pyarrow as pa
from deltalake import write_deltalake
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
cap_tbl = os.path.join(BASE, "bronze_capturabilidad")

con = duckdb.connect()

# 1) Resumen por vertical: % capturable, profundidad media, spread medio
res = con.execute("""
  SELECT vertical,
         COUNT(*) n,
         SUM(book_valido) n_capturable,
         ROUND(100.0*SUM(book_valido)/COUNT(*),1) pct_capturable,
         ROUND(AVG(CASE WHEN book_valido=1 THEN profundidad END),1) profundidad_media,
         ROUND(AVG(CASE WHEN book_valido=1 THEN spread END),4) spread_medio
  FROM delta_scan('%s')
  GROUP BY vertical
""" % cap_tbl).fetchall()
print("== CAPTURABILIDAD POR VERTICAL ==")
for v,n,nc,pct,prof,spr in res:
    print("  %-12s n=%s capturable=%s (%.1f%%) profundidad_media=%s spread=%s"
          % (v,n,nc,pct,prof,spr))

# 2) Top mercados no-deportivos con book y su spread (los que serian utilizables)
print("\n== TOP NO-DEPORTIVOS CAPTURABLES (por volumen) ==")
rows = con.execute("""
  SELECT question, vol24, niveles_bids, niveles_asks, mejor_bid, mejor_ask,
         ROUND(spread,4) spread, ROUND(profundidad,1) profundidad
  FROM delta_scan('%s')
  WHERE vertical='no-deportivo' AND book_valido=1
  ORDER BY vol24 DESC
""" % cap_tbl).fetchall()
for q,v,nb,na,bb,ba,spr,prof in rows[:15]:
    print("  vol=%s spread=%s prof=%s :: %s" % (round(v or 0), spr, prof, (q or "")[:65]))

# 3) No-deportivos que NO tienen book (falla la capturabilidad)
print("\n== NO-DEPORTIVOS SIN BOOK ==")
bad = con.execute("""
  SELECT question, vol24 FROM delta_scan('%s')
  WHERE vertical='no-deportivo' AND book_valido=0
""" % cap_tbl).fetchall()
for q,v in bad:
    print("  vol=%s :: %s" % (round(v or 0), (q or "")[:60]))
if not bad:
    print("  (ninguno: los 20 no-deportivos consultados todos tienen book)")

# gold capturabilidad agregado
gold = con.execute("""
  SELECT vertical, COUNT(*) n, SUM(book_valido) n_capturable,
         ROUND(100.0*SUM(book_valido)/COUNT(*),1) pct_capturable
  FROM delta_scan('%s') GROUP BY vertical
""" % cap_tbl).fetchall()
gpath = os.path.join(BASE, "gold_capturabilidad_vertical")
write_deltalake(gpath, pa.Table.from_pylist([
    {"vertical":g[0],"n":g[1],"n_capturable":g[2],"pct_capturable":g[3]} for g in gold
]), mode="overwrite")
print("\nGOLD capturabilidad ->", gpath)
