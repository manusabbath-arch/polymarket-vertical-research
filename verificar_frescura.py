import os, duckdb, datetime
from deltalake import write_deltalake
import pyarrow as pa

BASE = "/home/mamba/vertical-exploration/delta"
tbl = os.path.join(BASE, "bronze_resoluciones")
con = duckdb.connect()

# HOY real (no hardcodeado)
hoy = datetime.datetime.now(datetime.timezone.utc).isoformat()
print("HOY (UTC):", hoy[:19])

# Cuantos de los 'resueltos' tienen endDate en el futuro (resolucion anticipada) vs pasado
fut = con.execute(
    "SELECT COUNT(*) FROM delta_scan('%s') WHERE vertical='no-deportivo' AND resuelto=1 "
    "AND endDate > '%s'" % (tbl, hoy)).fetchone()[0]
pas = con.execute(
    "SELECT COUNT(*) FROM delta_scan('%s') WHERE vertical='no-deportivo' AND resuelto=1 "
    "AND endDate <= '%s'" % (tbl, hoy)).fetchone()[0]
print("RESUELTOS con endDate FUTURO (>=hoy): %s  <- resolucion anticipada / no natural" % fut)
print("RESUELTOS con endDate PASADO (<hoy):  %s <- eventos que pasaron realmente" % pas)

pct_futuro = 100.0 * fut / (fut + pas) if (fut + pas) else 0.0
print("pct de resoluciones con endDate futuro: %.1f%%" % pct_futuro)

# Para backtest precio-vs-resultado NATURAL solo cuentan los de endDate pasado
print("\n== CHECK: dataset de backtest NATURAL (endDate pasado) ==")
if pas >= 200:
    print("   n_natural=%s >= 200: hay muestra real para backtestear edge" % pas)
    # distribucion temporal de los naturales
    rng = con.execute(
        "SELECT MIN(substr(endDate,1,10)), MAX(substr(endDate,1,10)), COUNT(DISTINCT substr(endDate,1,10)) "
        "FROM delta_scan('%s') WHERE vertical='no-deportivo' AND endDate <= '%s' AND resuelto=1"
        % (tbl, hoy)).fetchone()
    print("   rango natural: min=%s max=%s dias=%s" % (rng[0], rng[1], rng[2]))
else:
    print("   n_natural=%s < 200: NO hay muestra suficiente de eventos realmente pasados" % pas)

# gold frescura
gold = pa.Table.from_pylist([{"n_resuelto_futuro": fut, "n_resuelto_pasado": pas,
                              "pct_endDate_futuro": round(pct_futuro,1)}])
write_deltalake(os.path.join(BASE, "gold_frescura_resolucion"), gold, mode="overwrite")
print("\nGold frescura persistido.")
