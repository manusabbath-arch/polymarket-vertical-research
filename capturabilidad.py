import os, json, urllib.request, urllib.parse, time, pyarrow as pa
from deltalake import write_deltalake, DeltaTable
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
CLOB = "https://clob.polymarket.com"

def fetch(url, retries=2, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent":"captura-explorer/1.0"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if a == retries-1:
                return {"_error": str(e)}
            time.sleep(1.2*a)

# ---- 1) Ingrego mercados Polymarket con token ids (no-deportivo + deportivo para comparar) ----
pm = fetch("https://gamma-api.polymarket.com/markets?limit=100&closed=false&order=volume24hr&ascending=false")
rows = []
if isinstance(pm, list):
    for m in pm:
        q = m.get("question","")
        tags = " ".join(m.get("tags") or []) + " " + (m.get("category") or "")
        sportish = any(s in (tags+q).lower() for s in ["nfl","nba","mlb","nhl","soccer","football","tennis",
                        "sports","ncaa","wnba","ufc","boxing","cricket","rugby","formula","f1","nascar"])
        # tokens: clobTokenIds JSON -> [yes, no]
        try:
            tok = json.loads(m.get("clobTokenIds")) if isinstance(m.get("clobTokenIds"), str) else (m.get("clobTokenIds") or [])
        except Exception:
            tok = []
        yes_tok = tok[0] if isinstance(tok, list) and tok else None
        rows.append({
            "fuente": "polymarket", "vertical": "sport" if sportish else "no-deportivo",
            "categoria": m.get("category") or "",
            "question": q, "vol24": m.get("volume24hr"),
            "clob_token_yes": yes_tok,
            "cond": m.get("conditionId"), "end": m.get("endDate"),
            "liquidez_quote": m.get("liquidity"), "ts": time.time()
        })
else:
    print("PM err:", pm.get("_error"))

print("PM mercados:", len(rows), "| no-deportivo:", sum(1 for r in rows if r['vertical']=='no-deportivo'),
      "sport:", sum(1 for r in rows if r['vertical']=='sport'))
print("PM con token:", sum(1 for r in rows if r['clob_token_yes']))

# ---- 2) Capturabilidad: consulto /book por cada token (muestra acotada) ----
# tomo hasta 20 no-deportivos top volumen + 10 deportivos para comparar
sel_ns = sorted([r for r in rows if r['vertical']=='no-deportivo' and r['clob_token_yes']],
                key=lambda r: r['vol24'] or 0, reverse=True)[:20]
sel_sp = sorted([r for r in rows if r['vertical']=='sport' and r['clob_token_yes']],
                key=lambda r: r['vol24'] or 0, reverse=True)[:10]
captura = []
for r in sel_ns + sel_sp:
    tok = r['clob_token_yes']
    book = fetch(CLOB + "/book?token_id=" + urllib.parse.quote(tok))
    if "_error" in book:
        captura.append({**{k:r[k] for k in ("fuente","vertical","categoria","question")},
                        "clob_token_yes":tok,"vol24":r["vol24"],
                        "book_valido":0,"niveles_bids":0,"niveles_asks":0,"mejor_bid":None,"mejor_ask":None,
                        "profundidad":0,"error":book["_error"]})
        continue
    bids = [b for b in (book.get("bids") or []) if b.get("price") is not None or b.get("size") is not None]
    asks = [a for a in (book.get("asks") or []) if a.get("price") is not None or a.get("size") is not None]
    best_bid = max([float(b["price"]) for b in bids if b.get("price")], default=None) if bids else None
    best_ask = min([float(a["price"]) for a in asks if a.get("price")], default=None) if asks else None
    depth = sum(float(b.get("size") or 0) for b in bids) + sum(float(a.get("size") or 0) for a in asks)
    captura.append({**{k:r[k] for k in ("fuente","vertical","categoria","question")},
                    "clob_token_yes":tok,"vol24":r["vol24"],
                    "book_valido":1 if (bids or asks) else 0,
                    "niveles_bids":len(bids),"niveles_asks":len(asks),
                    "mejor_bid":best_bid,"mejor_ask":best_ask,"profundidad":depth,
                    "spread": (best_ask-best_bid) if (best_bid and best_ask) else None})

# ---- 3) Persisto bronze capturabilidad ----
cap_arrow = pa.Table.from_pylist(captura)
cap_tbl = os.path.join(BASE, "bronze_capturabilidad")
write_deltalake(cap_tbl, cap_arrow, mode="overwrite")
print("\nCapturabilidad consultada para", len(captura), "mercados ->", cap_tbl)
