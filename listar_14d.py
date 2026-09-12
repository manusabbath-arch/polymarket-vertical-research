import urllib.request, json, collections, datetime, time
import urllib.parse

def fetch(u):
    req = urllib.request.Request(u, headers={'User-Agent':'probe/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

today = datetime.datetime(2026, 9, 12, tzinfo=datetime.timezone.utc)
d = fetch('https://gamma-api.polymarket.com/markets?limit=200&closed=false&order=volume24hr&ascending=false')

# los que resuelven dentro de 14 dias, ordenados por volumen
cortos = []
for m in d:
    ed = m.get('endDate', '')
    try:
        end = datetime.datetime.fromisoformat(ed.replace('Z','+00:00'))
        days = (end - today).days
    except Exception:
        continue
    if 0 < days <= 14:
        # clasificar no-deportivo
        q = m.get('question','') or ''
        tags = ' '.join(m.get('tags') or []) + ' ' + (m.get('category') or '')
        sportish = any(s in (tags+q).lower() for s in
            ["nfl","nba","mlb","nhl","soccer","football","tennis","sports",
             "ncaa","wnba","ufc","boxing","cricket","rugby","formula","f1",
             "nascar","esports","cs2","valorant","lol","dota"])
        cortos.append({"days": days, "q": q, "sport": sportish,
                       "vol": m.get("volume24hr") or 0,
                       "cat": m.get("category") or m.get("primaryCategory") or ""})

cortos.sort(key=lambda r: r["vol"], reverse=True)
print("== MERCADOS QUE RESUELVEN EN <=14d (n=%s) ==" % len(cortos))
n_ns = 0
for r in cortos[:35]:
    tag = "SPORT" if r["sport"] else "nosport"
    if not r["sport"]:
        n_ns += 1
    print("  d=%2s vol=%10s [%s] %s" % (r["days"], round(r["vol"]), tag, r["q"][:66]))
print("\nno-deportivos en <=14d:", n_ns, "de", len(cortos))

# persistir listado
import pyarrow as pa
from deltalake import write_deltalake
rows = [{"days": r["days"], "titulo": r["q"], "sport": r["sport"], "vol24h": r["vol"]} for r in cortos]
write_deltalake("/home/mamba/vertical-exploration/delta/bronze_resolucion_14d",
                pa.Table.from_pylist(rows), mode="overwrite")
