import os, datetime, pyarrow as pa, json
from deltalake import write_deltalake
from pmxt import Polymarket
pm = Polymarket()

today = datetime.datetime(2026, 9, 12, tzinfo=datetime.timezone.utc)

# Mercados geo/politica resueltos recientemente (del find_resolved) + capturar resultado final
RESOLVED = [
    ("Strait of Hormuz by September 15", "geo", "792896940617", -3),
    ("Strait Sept 30", "geo", "235451931222", -18),
    ("Which month Sept", "geo", "113508646298", None),
    ("Iran blockade before Xi", "geo", "941701433922", -111),
    ("Hormuz by October 31", "geo", "653180427933", -49),
]

rows = []
for label, cat, oid, ds in RESOLVED:
    try:
        trades = pm.fetch_trades(outcome_id=oid, limit=500)
    except Exception as e:
        print("%s trades ERR %s" % (label, repr(e)[:120]))
        continue
    if not trades:
        print("%s sin trades" % label)
        continue
    # series de precios (yes) ordenados por timestamp
    s = sorted([(t.timestamp or 0, t.price, t.side, t.amount) for t in trades], key=lambda x: x[0])
    if not s:
        continue
    precio_max = max(x[1] for x in s if x[1])
    precio_min = min(x[1] for x in s if x[1] and x[1] > 0)
    # resultado final: inferir del ultimo trade/estado -> usar price de cierre del trade mas nuevo
    last_price = s[-1][1]
    # asumimos resultado = el extremo al que converge el precio final (0 o 1, con umbral)
    resolved_yes = 1 if last_price >= 0.98 else (0 if last_price <= 0.02 else None)
    rows.append({
        "mercado": label, "categoria": cat, "clob_token_id": oid,
        "n_trades": len(s), "precio_min": round(precio_min,4), "precio_max": round(precio_max,4),
        "last_price": last_price, "resolved_yes": resolved_yes,
    })
    print("  %-42s n=%3d pmin=%s pmax=%s last=%s res_yes=%s" %
          (label[:42], len(s), round(precio_min,3), round(precio_max,3), last_price, resolved_yes))

if rows:
    write_deltalake("/home/mamba/vertical-exploration/delta/bronze_backtest_resolved",
                    pa.Table.from_pylist(rows), mode="overwrite")
    print("\nPersistido bronze_backtest_resolved")
