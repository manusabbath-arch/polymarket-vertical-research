import os, duckdb, collections
BASE = "/home/mamba/vertical-exploration/delta"
con = duckdb.connect()

# universo acumulado + snapshots acumulados
uni = os.path.join(BASE, "forward_universo")
snap = os.path.join(BASE, "forward_snapshots")
n_uni = con.execute("SELECT COUNT(DISTINCT market_id) FROM delta_scan('%s')" % uni).fetchone()[0]
n_snap = con.execute("SELECT COUNT(*) FROM delta_scan('%s')" % snap).fetchone()[0]
n_ts = con.execute("SELECT COUNT(DISTINCT ts) FROM delta_scan('%s')" % snap).fetchone()[0]
print("Universo unico (mercados trackeados):", n_uni)
print("Snapshots acumulados (append):", n_snap, "| ciclos distintos:", n_ts)

# universo reciente por dias a resolucion
print("\n== Universo reciente por horizonte (vol>=10k, <=30d) ==")
rows = con.execute("""
  SELECT CASE WHEN days<=7 THEN '<=7d' WHEN days<=14 THEN '<=14d' WHEN days<=30 THEN '<=30d' END b,
         COUNT(DISTINCT market_id) n, ROUND(SUM(vol24h)) vol
  FROM delta_scan('%s') GROUP BY b ORDER BY b
""" % uni).fetchall()
for b,n,v in rows:
    print("  %-6s n=%4s vol24h=%12s" % (b,n,v))

# categorias por texto de pregunta (aproximacion sin tags)
print("\n== Top temas por keyword (universo) ==")
qs = con.execute("SELECT DISTINCT question FROM delta_scan('%s')" % uni).fetchall()
kw = collections.Counter()
for (q,) in qs:
    ql = (q or "").lower()
    for k in ["fed","election","president","prime minister","us open","tennis","hormuz","iran",
              "baseball","nfl","basketball","soccer","football","brazil","sweden","world cup","champion"]:
        if k in ql:
            kw[k]+=1
for k,n in kw.most_common(18):
    print("  %-16s n=%s" % (k,n))
