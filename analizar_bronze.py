import os, pyarrow as pa
from deltalake import write_deltalake
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
bronze = os.path.join(BASE, "bronze_verticales")

con = duckdb.connect()
tbl = con.execute(
    "SELECT fuente, COALESCE(categoria,'(sin cat)') c, COUNT(*) n "
    "FROM delta_scan('%s') GROUP BY fuente, c ORDER BY n DESC" % bronze
).fetchall()
print("== RIQUEZA POR FUENTE/CATEGORIA (bronze real) ==")
for f, c, n in tbl:
    print("  %-12s %-28s n=%s" % (f, c, n))

preguntas = con.execute(
    "SELECT fuente, question, vol24 FROM delta_scan('%s') WHERE question IS NOT NULL "
    "ORDER BY vol24 DESC NULLS LAST" % bronze
).fetchall()
print("\n== MUESTRA PREGUNTAS: TOP VOLUMEN (no-deportivo) ==")
n_nd = 0
for f, q, v in preguntas:
    if n_nd >= 15:
        break
    print("  [%s] vol=%s :: %s" % (f, v, (q or "")[:88]))
    n_nd += 1

g_rows = con.execute(
    "SELECT fuente, vertical, COUNT(*) n, COUNT(vol24) n_vol, COALESCE(SUM(vol24),0) suma_vol "
    "FROM delta_scan('%s') WHERE vertical != 'sport' "
    "GROUP BY fuente, vertical ORDER BY suma_vol DESC NULLS LAST" % bronze
).fetchall()
gold = pa.Table.from_pylist([
    {"fuente": g[0], "vertical": g[1], "n": g[2], "n_con_vol": g[3], "suma_vol24": g[4]}
    for g in g_rows
])
gpath = os.path.join(BASE, "gold_riqueza_vertical")
write_deltalake(gpath, gold, mode="overwrite")
print("\n== GOLD: riqueza vertical no-deportiva (materializada) ==")
for r in g_rows:
    print("  %-12s %-12s n=%s con_vol=%s suma_vol24=%s" % (r[0], r[1], r[2], r[3], r[4]))
print("\nGOLD persistido en", gpath)
