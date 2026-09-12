import os, json, time, pyarrow as pa
from deltalake import write_deltalake, DeltaTable
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
tbl = os.path.join(BASE, "bronze_backtest_vertical_pm")

# Queries de vertical no-deportiva con suficiente volumen
QUERIES = [
    ("Fed interest rates", "economia"),
    ("president", "politics"),
    ("election", "politics"),
]

rows = []
from pmxt import Polymarket
pm = Polymarket()

for q, cat in QUERIES:
    try:
        ms = pm.fetch_markets(query=q, limit=8)
    except Exception as e:
        print("query %s ERR %s" % (q, repr(e)[:120]))
        continue
    for m in ms:
        oid = m.outcomes[0].outcome_id if m.outcomes else None
        if not oid:
            continue
        record = {
            "fuente": "polymarket", "vertical": "no-deportivo", "categoria": cat,
            "market_id": m.market_id, "slug": m.slug, "titulo": m.title,
            "clob_token_id": oid, "volume": m.volume, "volume_24h": m.volume_24h,
            "liquidity": m.liquidity, "resolution_date": m.resolution_date,
            "yes_price_now": (m.outcomes[0].price if m.outcomes else None),
        }
        # intentar candles historicas
        try:
            candles = pm.fetch_ohlcv(outcome_id=oid, resolution="1d", limit=90)
            record["n_candles"] = len(candles) if candles else 0
            if candles:
                # close mas reciente + primera de la ventana
                record["close_reciente"] = candles[-1].close
                record["close_ventana_hace"] = candles[0].close
                record["fecha_reciente"] = candles[-1].timestamp
        except Exception as e:
            record["n_candles"] = -1
            record["candle_error"] = repr(e)[:120]
        rows.append(record)
        print("  + %s | %s | n_candles=%s | yes_ahora=%s" %
              (cat, m.title[:45], record.get("n_candles"), record.get("yes_price_now")))
        time.sleep(0.3)

print("\nTOTAL backtest:", len(rows))
if rows:
    arrow = pa.Table.from_pylist(rows)
    write_deltalake(tbl, arrow, mode="overwrite")
    print("Persistido:", tbl)
