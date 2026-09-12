import os, datetime, json, time
import pyarrow as pa
from deltalake import write_deltalake

# Mercado de la vertical YA resuelto -> backtest precio-vs-resultado inmediato
# Strait of Hormuz (geoestrategia) y politicas recientes se resolvieron. Buscamos resolvidos.
from pmxt import Polymarket
pm = Polymarket()

# 1) Buscar mercados de geoestrategia/politica con status cerrado/activo y endDate pasada reciente
CANDS = [
    ("Iran", "geo"),
    ("Sweden", "politics"),
    ("Hormuz", "geo"),
    ("prime minister", "politics"),
]
for query, cat in CANDS:
    try:
        ms = pm.search_events(query) if hasattr(pm, "search_events") else None
        break
    except Exception:
        ms = None
        break

# fallback: fetch_markets con query
hits = []
today = datetime.datetime(2026, 9, 12, tzinfo=datetime.timezone.utc)
for query, cat in [("Strait of Hormuz", "geo"), ("Iran blockade", "geo"), ("Sweden prime minister", "politics")]:
    try:
        ms = pm.fetch_markets(query=query, limit=8)
        for m in ms:
            rd = getattr(m, "resolution_date", None)
            if rd is None:
                continue
            try:
                end = rd if rd.tzinfo else rd.replace(tzinfo=datetime.timezone.utc)
                days = (today - end).days
            except Exception:
                continue
            hits.append({"m": m, "cat": cat, "days_since_resolved": days, "query": query})
    except Exception as e:
        print("query %s ERR %s" % (query, repr(e)[:100]))

print("== mercados resueltos recientemente (<=30d) ==")
recent = [h for h in hits if h["days_since_resolved"] <= 30]
for h in sorted(recent, key=lambda x: x["days_since_resolved"]):
    m = h["m"]
    oid = m.outcomes[0].outcome_id if m.outcomes else None
    print("  %4d dias atras [%s] %s | oid=%s" %
          (h["days_since_resolved"], h["cat"], m.title[:60], (oid or "")[:12]))
