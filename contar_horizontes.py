import urllib.request, json, collections, datetime, time

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
# paginar mas profundo para contar por horizonte
mercados = []
for offset in range(0, 2000, 100):
    d = fetch("https://gamma-api.polymarket.com/markets?limit=100&offset=%d&closed=false&order=volume24hr&ascending=false" % offset)
    if not isinstance(d, list) or not d:
        break
    mercados.extend(d)
    if len(d) < 100:
        break
    time.sleep(0.4)

print("mercados totales muestreados:", len(mercados))

# por horizonte de resolucion, no-deportivo con token
buckets = collections.defaultdict(int)
buckets_vol = collections.defaultdict(float)
for m in mercados:
    ed = m.get('endDate','')
    try:
        end = datetime.datetime.fromisoformat(ed.replace('Z','+00:00'))
        days = (end - today).days
    except:
        days = None
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
    if days is None:
        b = 'sin_fecha'
    elif days <= 7: b = '<=7d'
    elif days <= 14: b = '<=14d'
    elif days <= 30: b = '<=30d'
    elif days <= 90: b = '<=90d'
    else: b = '>90d'
    buckets[b] += 1
    buckets_vol[b] += m.get('volume24hr') or 0

print("== mercados no-deportivo VIVOS con token por horizonte ==")
for b in ['<=7d','<=14d','<=30d','<=90d','>90d','sin_fecha']:
    print("  %-8s n=%5s vol24h=%12s" % (b, buckets[b], round(buckets_vol[b])))
