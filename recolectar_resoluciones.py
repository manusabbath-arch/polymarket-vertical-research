import os, json, urllib.request, urllib.parse, time, pyarrow as pa
from deltalake import write_deltalake, DeltaTable
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
SPORTISH = ["nfl","nba","mlb","nhl","soccer","football","tennis",
            "sports","ncaa","wnba","ufc","boxing","cricket","rugby",
            "formula","f1","nascar","esports","cs2","valorant","lol","dota"]

def fetch(url, retries=3, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent":"resolucion-explorer/1.0"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if a == retries-1:
                return {"_error": str(e)}
            time.sleep(1.2*(a+1))

def es_deportivo(q, tags):
    t = (tags + " " + q).lower()
    return any(s in t for s in SPORTISH)

def normalizar_outcome(prices):
    """outcomePrices -> lista de floats; None si no resuelto"""
    if not prices:
        return None
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except Exception:
            return None
    out = []
    for p in prices:
        try:
            out.append(float(p))
        except (TypeError, ValueError):
            out.append(None)
    return out if any(v is not None for v in out) else None

# Recolectar mercados cerrados paginado (hasta N paginas, sin sobrepasar)
TODAS = []
PAGE = 100
for offset in range(0, 1200, PAGE):
    url = ("https://gamma-api.polymarket.com/markets?limit=%d&offset=%d&closed=true"
           "&order=endDate&ascending=false" % (PAGE, offset))
    d = fetch(url)
    if isinstance(d, list) and d:
        TODAS.extend(d)
        # detener si la ultima pagina devolvio menos que el limite
        if len(d) < PAGE:
            break
    else:
        break
    time.sleep(0.3)

print("Mercados cerrados recolectados:", len(TODAS))

rows = []
for m in TODAS:
    q = m.get("question","") or ""
    tags = " ".join(m.get("tags") or []) + " " + (m.get("category") or "")
    dep = es_deportivo(q, tags)
    out = normalizar_outcome(m.get("outcomePrices"))
    resolved = 1 if out is not None else 0
    rows.append({
        "fuente":"polymarket",
        "vertical":"sport" if dep else "no-deportivo",
        "categoria": m.get("category") or (m.get("primaryCategory") or ""),
        "question": q,
        "endDate": m.get("endDate"),
        "closed": m.get("closed"),
        "outcome_normalizado": out,
        "resuelto": resolved,
        "volume": m.get("volume24hr") if m.get("volume24hr") else m.get("liquidity"),
    })

arrow = pa.Table.from_pylist(rows)
tbl = os.path.join(BASE, "bronze_resoluciones")
write_deltalake(tbl, arrow, mode="overwrite")
print("Persistido a:", tbl, "| total:", len(rows),
      "| no-deportivo:", sum(1 for r in rows if r["vertical"]=="no-deportivo"),
      "| sport:", sum(1 for r in rows if r["vertical"]=="sport"))
