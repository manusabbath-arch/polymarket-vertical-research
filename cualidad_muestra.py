import urllib.request, json, datetime, time

def fetch(u):
    req = urllib.request.Request(u, headers={'User-Agent':'probe/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

SPORTISH = ["nfl","nba","mlb","nhl","soccer","football","tennis","sports",
            "ncaa","wnba","ufc","boxing","cricket","rugby","formula","f1","nascar"]
def es_deportivo(q, tags):
    t = (tags + " " + q).lower()
    return any(s in t for s in SPORTISH)

today = datetime.datetime(2026, 9, 12, tzinfo=datetime.timezone.utc)
mercados = []
for offset in range(0, 2000, 100):
    d = fetch("https://gamma-api.polymarket.com/markets?limit=100&offset=%d&closed=false&order=volume24hr&ascending=false" % offset)
    if not isinstance(d, list) or not d:
        break
    mercados.extend(d)
    if len(d) < 100:
        break
    time.sleep(0.4)

# filtrar no-deportivo + horizonte <=30d + medir por umbral de liquidez
cands = []
for m in mercados:
    ed = m.get('endDate','')
    try:
        end = datetime.datetime.fromisoformat(ed.replace('Z','+00:00'))
        days = (end - today).days
    except:
        continue
    if not (0 < days <= 30):
        continue
    q = m.get('question','') or ''
    tags = ' '.join(m.get('tags') or []) + ' ' + (m.get('category') or '')
    if es_deportivo(q, tags):
        continue
    try:
        tok = json.loads(m.get('clobTokenIds')) if isinstance(m.get('clobTokenIds'),str) else (m.get('clobTokenIds') or [])
        yes = tok[0] if isinstance(tok,list) and tok else None
    except:
        yes = None
    if not yes:
        continue
    vol = m.get('volume24hr') or 0
    liq = m.get('liquidity') or 0
    cands.append({"days":days,"vol":vol,"liq":liq,"q":q,"token":yes})

print("candidatos no-deportivo <=30d con token:", len(cands))
for minvol in [0, 1000, 5000, 10000, 50000]:
    n = sum(1 for c in cands if c["vol"] >= minvol)
    sumvol = sum(c["vol"] for c in cands if c["vol"] >= minvol)
    print("  vol24h >= %7d -> n=%4s | sum_vol=%s | (dias max=%s)" %
          (minvol, n, round(sumvol), max((c["days"] for c in cands if c["vol"]>=minvol), default=0)))
print("\n== top 20 por volumen (<=30d) con token ==")
for c in sorted(cands, key=lambda x:x["vol"], reverse=True)[:20]:
    try:
        liq = round(float(c["liq"]))
    except (TypeError, ValueError):
        liq = 0
    print("  d=%2s vol=%10s liq=%10s :: %s" % (c["days"], round(c["vol"]), liq, c["q"][:58]))
