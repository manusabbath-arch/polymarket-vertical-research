"""
Recolector forward de la vertical no-deportiva de resolucion cercana.

Objetivo: medir edge SIN esperar 2028. Cada ciclo captura (para mercados que resuelven
en <=14 dias) su book real del CLOB, y persiste un snapshot con timestamp. Cuando el
mercado se resuelve, el registro queda. Con N ciclos en los dias previos y luego la
resolucion, se puede evaluar entrada-vs-resultado sobre datos naturales limpios.

Uso:
    pip install pmxt deltalake duckdb pyarrow
    python recolector_forward.py            # ciclo manual
"""
import os, json, time, datetime, sys, urllib.request
import pyarrow as pa
from deltalake import write_deltalake, DeltaTable
import duckdb

BASE = "/home/mamba/vertical-exploration/delta"
SNAP_TBL = os.path.join(BASE, "forward_snapshots")
HORIZON_DAYS = 30          # ampliado: de 14 -> 30 dias (209 mercados ejecutables)
MIN_VOL24H = 10000.0       # filtro de liquidez: descarta mercados < $10k vol24h (injectados)
TOP_SNAPSHOT = 40          # cuantos books capturar por ciclo (rate-limited, ~15-20s)
TODAY = datetime.datetime(2026, 9, 12, tzinfo=datetime.timezone.utc)

# ---- fuentes de merados a trackear: Gamma top-volumen con endDate proximo ----
def fetch(url, retries=2, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "forward-explorer/1.0"})
    for a in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if a == retries - 1:
                return {"_error": str(e)}
            time.sleep(1.2 * a)

SPORTISH = ["nfl","nba","mlb","nhl","soccer","football","tennis","sports",
            "ncaa","wnba","ufc","boxing","cricket","rugby","formula","f1",
            "nascar"]  # esports no: queremos no-deportivo

def es_deportivo(q, tags):
    t = (tags + " " + q).lower()
    return any(s in t for s in SPORTISH)

def mercado_a_trackear():
    """Mercados abiertos con endDate en (0, HORIZON] dias y vol24h >= MIN_VOL24H,
    ordenados por volumen. Recorre hasta 2000 mercados top-volumen (cubre el universo 30d)."""
    todos = []
    for offset in range(0, 2000, 100):
        d = fetch("https://gamma-api.polymarket.com/markets?limit=100&offset=%d&closed=false&order=volume24hr&ascending=false" % offset)
        if isinstance(d, list) and d:
            todos.extend(d)
            if len(d) < 100:
                break
        else:
            break
        time.sleep(0.35)
    out = []
    for m in todos:
        ed = m.get("endDate", "")
        try:
            end = datetime.datetime.fromisoformat(ed.replace("Z", "+00:00"))
            days = (end - TODAY).days
        except Exception:
            continue
        if not (0 < days <= HORIZON_DAYS):
            continue
        q = m.get("question", "") or ""
        tags = " ".join(m.get("tags") or []) + " " + (m.get("category") or "")
        if es_deportivo(q, tags):
            continue
        # token yes desde clobTokenIds
        try:
            tok = json.loads(m.get("clobTokenIds")) if isinstance(m.get("clobTokenIds"), str) else (m.get("clobTokenIds") or [])
            yes_tok = tok[0] if isinstance(tok, list) and tok else None
        except Exception:
            yes_tok = None
        if not yes_tok:
            continue
        # filtro de liquidez: descarta mercados con volumen 24h bajo (inuplables)
        vol24h = m.get("volume24hr") or 0
        if vol24h < MIN_VOL24H:
            continue
        out.append({
            "market_id": m.get("id"), "question": q, "endDate": ed, "days": days,
            "clob_token_yes": yes_tok, "vol24h": vol24h,
        })
    out.sort(key=lambda r: r["vol24h"], reverse=True)
    return out

# ---- captura book real del CLOB ----
def captura_book(token_id):
    from pmxt import Polymarket
    pm = Polymarket()
    try:
        ob = pm.fetch_order_book(outcome_id=token_id, limit=2) if hasattr(pm, "fetch_order_book") else None
        if ob is None:
            # fallback raw
            ob = pm.fetch_order_book(outcome_id=token_id)
        return ob
    except Exception as e:
        return {"_error": str(e)}

def run_ciclo():
    mercados = mercado_a_trackear()
    print("== Mercados a trackear (resuelven en <= %dd) n=%s ==" % (HORIZON_DAYS, len(mercados)))
    for mr in mercados[:20]:
        print("  d=%2s vol=%10s :: %s" % (mr["days"], round(mr["vol24h"]), mr["question"][:60]))

    # guardar universo a trackear (append: universo creciente entre ciclos; dedup por market_id)
    uni_arrow = pa.Table.from_pylist([{"market_id": m["market_id"], "question": m["question"],
                                       "endDate": m["endDate"], "days": m["days"],
                                       "clob_token_yes": m["clob_token_yes"], "vol24h": m["vol24h"],
                                       "ts_universo": int(time.time())} for m in mercados])
    uni_tbl = os.path.join(BASE, "forward_universo")
    if os.path.isdir(uni_tbl):
        write_deltalake(uni_tbl, uni_arrow, mode="append")
    else:
        write_deltalake(uni_tbl, uni_arrow, mode="overwrite")

    # snapshot de book para los de mayor volumen (evita N queries, rate-limited)
    TOP = TOP_SNAPSHOT if "--all" not in sys.argv else 80
    snap_rows = []
    n_ok = 0
    for mr in mercados[:TOP]:
        ob = captura_book(mr["clob_token_yes"])
        if isinstance(ob, dict) and "_error" in ob:
            best_bid = best_ask = spread = depth = nivel = None
            err = ob["_error"]
        else:
            n_ok += 1
            # pmxt OrderBook: best_bid/best_ask o bids/asks
            bb = getattr(ob, "best_bid", None); ba = getattr(ob, "best_ask", None)
            if bb is None and hasattr(ob, "bids"):
                b = ob.bids or []
                a = ob.asks or []
                bb = b[0].price if b else None
                ba = a[0].price if a else None
                nivel = min(len(b), len(a))
                depth = sum(x.size for x in b) + sum(x.size for x in a)
            else:
                nivel = None
            best_bid, best_ask, spread, err = bb, ba, (ba - bb if bb and ba else None), None
        snap_rows.append({
            "market_id": mr["market_id"], "question": mr["question"],
            "clob_token_yes": mr["clob_token_yes"], "vol24h": mr["vol24h"],
            "days_a_resolver": mr["days"], "endDate": mr["endDate"],
            "best_bid": best_bid, "best_ask": best_ask,
            "spread": spread, "profundidad": depth, "error": str(err) if err else None,
            "ts": int(time.time()),
        })
        time.sleep(0.3)

    # append a snapshots historicos (append-only: un snapshot por ciclo por mercado)
    # forzar error como string (si todo None -> void rompe delta_scan)
    arrow = pa.Table.from_pylist(snap_rows)
    if "error" in arrow.column_names and arrow.schema.field("error").type == pa.null():
        import pyarrow as _pa
        nones = [None] * arrow.num_rows
        arrow = arrow.set_column(arrow.schema.get_field_index("error"),
                                 "error", _pa.array(nones, type=_pa.string()))
    if os.path.isdir(SNAP_TBL):
        write_deltalake(SNAP_TBL, arrow, mode="append")
    else:
        write_deltalake(SNAP_TBL, arrow, mode="overwrite")
    print("\nSnapshots del ciclo: %s -> %s (append)" % (len(snap_rows), SNAP_TBL))

    # reporte resumido con duckdb
    con = duckdb.connect()
    latest = con.execute("""
        SELECT question, endDate, ROUND(best_bid,3) bid, ROUND(best_ask,3) ask,
               ROUND(spread,4) spread, ROUND(profundidad,0) depth
        FROM delta_scan('%s')
        WHERE ts = (SELECT MAX(ts) FROM delta_scan('%s'))
        ORDER BY profundidad DESC NULLS LAST
        LIMIT 15
    """ % (SNAP_TBL, SNAP_TBL)).fetchall()
    print("\n== Ultimo snapshot (top profundidad) ==")
    for q, ed, bid, ask, spr, dep in latest:
        print("  bid=%s ask=%s spr=%s dep=%8.0f d=%s :: %s" %
              (bid, ask, spr, dep or 0, (ed or "")[:10], (q or "")[:50]))

if __name__ == "__main__":
    run_ciclo()
