import os, json, datetime, collections
import pyarrow as pa
from deltalake import write_deltalake
from pmxt import Polymarket
pm = Polymarket()

# Mercados geoestrategia resueltos (n=5, todos res_yes=1) -> trades historicos
MERCADOS = [
    ("Strait Sept 15", "geo", "792896940617"),
    ("Strait Sept 30", "geo", "235451931222"),
    ("Which month Sept", "geo", "113508646298"),
    ("Iran before Xi", "geo", "941701433922"),
    ("Hormuz Oct 31", "geo", "653180427933"),
]

all_trades = []
for label, cat, oid in MERCADOS:
    trades = pm.fetch_trades(outcome_id=oid, limit=1000)
    if not trades:
        print(label, "sin trades")
        continue
    s = sorted([(t.timestamp or 0, t.price, t.side, t.amount or 0) for t in trades], key=lambda x: x[0])
    all_trades.append((label, oid, s))

print("== SERIES CARGADAS (mercados resueltos) ==")
for label, oid, s in all_trades:
    print("  %-20s n_trades=%s | p_first=%s p_last=%s | vol_sum=%s" %
          (label, len(s), round(s[0][1],3), round(s[-1][1],3), round(sum(x[3] for x in s),1)))

# Backtest simple: strategy 'comprar YES si precio < 0.x y mercado no resuelto, vender a resolucion'
# Para mercados resueltos=1 (todos), comprar a p<=0.5 y hold a resolucion paga 1.0
# EV = (frecuencia acierto) * payoff + (1-freq)*perdida, ambos netos de fees
# Capturabilidad real (medida antes): spread 0.005, profundidad 9.1M, fee taker ~0.7%
print("\n== BACKTEST: comprar YES <= umbral, hold a resolucion (mercados resueltos=1) ==")
resultados = []
for label, oid, s in all_trades:
    # cada trade de compra a precio <= umbral
    for umbral in [0.10, 0.20, 0.30, 0.40, 0.50]:
        compras = [t for t in s if t[2] == "buy" and t[1] <= umbral]
        if not compras:
            continue
        # P&L por compra: pagas p, recibis 1.0 si gana (res_yes=1)
        # fee taker Polymarket ~0.7% de notional
        fee = 0.007
        pnl_total = 0.0
        for _, p, _, amt in compras:
            # compras a precio p, se resuelve a 1.0
            pnl = (1.0 - p) * amt - fee * amt
            pnl_total += pnl
        n = len(compras)
        resultados.append({
            "mercado": label, "umbral": umbral, "n_compras": n,
            "pnl_total_usd": round(pnl_total,4),
            "ev_por_unidad": round(pnl_total / n if n else 0, 4),
            "res_yes": 1,
        })
        print("  %-20s umb<=%.2f n=%3d pnl_total=%8.2f ev/un=%8.4f" %
              (label, umbral, n, pnl_total, pnl_total / n if n else 0))

if resultados:
    write_deltalake("/home/mamba/vertical-exploration/delta/gold_backtest_vertical",
                    pa.Table.from_pylist(resultados), mode="overwrite")
    print("\nPersistido gold_backtest_vertical")
