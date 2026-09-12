import os, inspect, datetime, pyarrow as pa
from deltalake import write_deltalake
from pmxt import Polymarket
pm = Polymarket()

print("fetch_trades sig:", inspect.signature(pm.fetch_trades))
# mercado de geoestrategia resuelto -3 dias (Strait Sept 15)
oid = "792896940617"
try:
    trades = pm.fetch_trades(outcome_id=oid, limit=20)
    print("n_trades:", len(trades) if trades else 0)
    if trades:
        t = trades[0]
        print("campos trade:", [a for a in dir(t) if not a.startswith('_')])
        print("ejemplo:", getattr(t, 'created_time', None), "price", getattr(t, 'price', None), "side", getattr(t, 'side', None))
except Exception as e:
    print("fetch_trades ERR:", repr(e)[:250])
