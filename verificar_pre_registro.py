import os, pyarrow as pa
from deltalake import write_deltalake
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
tbl = os.path.join(BASE, "bronze_resoluciones")
con = duckdb.connect()

# ===== Verificacion vs PRE-REGISTRO =====
print("===== VERIFICACION PRE-REGISTRO (criteria fijados ANTES de ver datos) =====")
n = con.execute("SELECT COUNT(*) FROM delta_scan('%s') WHERE vertical='no-deportivo'" % tbl).fetchone()[0]
res_rate = con.execute(
    "SELECT ROUND(100.0*SUM(resuelto)/COUNT(*),1) FROM delta_scan('%s') WHERE vertical='no-deportivo'"
    % tbl).fetchone()[0]
sport_n = con.execute("SELECT COUNT(*) FROM delta_scan('%s') WHERE vertical='sport'" % tbl).fetchone()[0]
sport_rate = con.execute(
    "SELECT ROUND(100.0*SUM(resuelto)/COUNT(*),1) FROM delta_scan('%s') WHERE vertical='sport'"
    % tbl).fetchone()[0]
print("  n_cerrados_no_deportivo = %s (umbral success: >=200)" % n)
print("  resolucion_rate no-deportivo = %s%% (umbral success: >=95, kill: <90)" % res_rate)
print("  [sport ref] n=%s resolucion_rate=%s%%" % (sport_n, sport_rate))

# verdict
if n >= 200 and res_rate is not None and float(res_rate) >= 0.95:
    verdict = "SUCCESS — muestra suficiente y resolucion alta: hay dataset para backtestear edge"
elif n < 200 or (res_rate is not None and float(res_rate) < 0.90):
    verdict = "KILL — no hay muestra o los mercados no se resuelven"
else:
    verdict = "GRIS — n ok pero resolucion <95: remedir, no concluir"
print("  VERDICT ->", verdict)

# ===== Distribucion por categoria / resolucion =====
print("\n===== RESOLUCION POR CATEGORIA (top) =====")
cats = con.execute("""
  SELECT COALESCE(NULLIF(categoria,''),'(sin cat)') c, COUNT(*) n,
         SUM(resuelto) res, ROUND(100.0*SUM(resuelto)/COUNT(*),1) rate
  FROM delta_scan('%s') WHERE vertical='no-deportivo'
  GROUP BY c ORDER BY n DESC LIMIT 12
""" % tbl).fetchall()
for c,n2,r,rate in cats:
    print("  %-28s n=%4s resuelto=%4s rate=%s%%" % (c, n2, r, rate))

# ===== rango temporal (cuando se resolvieron) =====
print("\n===== RANGO TEMPORAL (endDate de no-deportivos) =====")
rng = con.execute("""
  SELECT MIN(endDate), MAX(endDate), COUNT(DISTINCT substr(endDate,1,10)) dias
  FROM delta_scan('%s') WHERE vertical='no-deportivo' AND endDate IS NOT NULL
""" % tbl).fetchone()
print("  min_end=%s  max_end=%s  dias_distintos=%s (frescura del dataset)" % (rng[0], rng[1], rng[2]))

# ===== muestra de mercados resueltos =====
print("\n===== MUESTRA RESUELTOS (outcome real) =====")
s = con.execute("""
  SELECT question, outcome_normalizado, substr(endDate,1,10) d
  FROM delta_scan('%s') WHERE vertical='no-deportivo' AND resuelto=1
  ORDER BY endDate DESC LIMIT 8
""" % tbl).fetchall()
for q,oc,d in s:
    print("  [%s] outcome=%s :: %s" % (d, oc, (q or "")[:70]))
