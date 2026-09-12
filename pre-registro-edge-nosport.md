# Pre-registro — Viabilidad de edge en vertical no-deportiva (Polymarket)

Fecha: 2026-09-11
Estado: PRE-REGISTRADO (criteria fijados ANTES de ver datos de resolución)
Estatus: TESTING propuesto (a medir)

## Claim

Polymarket no-deportivo (elecciones/economía) tiene mercados RICOS y CAPTURABLES (medido:
100% capturable, profundidad media 9.1M, spread 0.001-0.01). Este pre-registro fija si
esa vertical, ADEMÁS de rica, tiene edge: si los mercados se resuelven, y si hay muestra
histórica para backtestear un modelo de probabilidad contra el precio de cierre/consenso.

## N-vel de contexto ya medido (riqueza/capturabilidad, NO edge)

- Muestra 300 mercados vivos: PM 95 no-deportivos (US$36.7M vol24h), Manifold $15K (pobre),
  Kalshi no medible (endpoints distintos).
- Capturabilidad: 20/20 no-deportivos con book CLOB, profundidad media 9.1M, spread medio
  0.005 (vs sports 0.5M / 0.01).

## Hipótesis (lo que se va a probar)

1. `resolucion_rate`: los mercados no-deportivos cerrados se resuelven (outcomePrices no
   NULL/null) en alta proporción.
2. `backtest_rate`: hay suficientes mercados cerrados con resolución + precio para
   construir un dataset de backtest del modelo de probabilidad.
3. EDGE como hipótesis separada (NO promovida acá): un modelo de elecciones/economía
   genera EV neto >0. Requiere model_prob calibrado + capturabilidad, fase posterior.

## Métrica y criteria de veredicto

Veredicto sobre la MUESTRA de mercados cerrados no-deportivos (n>0, medido de la Gamma):

- Dataset suficiente si `n_cerrados_no_deportivos >= 200` (muestra mínima para una métrica
  estable de resolución) y `resolucion_rate >= 0.95`.
- `resolucion_rate = count(outcomePrices no nulo) / n_cerrados_no_deportivos`.

## Kill / Success criteria (PRE-REGISTRADOS)

- **KILL si** cualquiera de:
  - `n_cerrados_no_deportivos < 200` (no hay muestra para backtest).
  - `resolucion_rate < 0.90` (los mercados no se resuelven = datos inutilizables).
- **SUCCESS si**: `n_cerrados_no_deportivos >= 200` AND `resolucion_rate >= 0.95`.
- Zona GRIS (TESTING se mantiene, no promueve a SUPPORTED): 0.90 <= resolucion_rate < 0.95
  con n >= 200 — re-medir, no concluir.

## No-goals (explicitos)

- NO es sobre capturabilidad (ya medida OK).
- NO es sobre edge neto de un modelo (fase 2, requiere el paso de model_prob calibrado).
- NO decide vertical si n < 200: con n < 200 no hay nada que concluir, kill.

## Cómo se mide

`recolectar_resoluciones.py` en /home/mamba/vertical-exploration/: ingerir mercados
`closed=true` de la Gamma con `outcomePrices` y `endDate`, categorizar no-deportivo,
broncear, y calcular resolucion_rate + n por la query gold.

## Enmienda post-medición — HALLAZGO DE FRESCURA (2026-09-12)

El veredicto formal del pre-registro (SUCCESS, n=1181, rate=100%) está VICIADO por el sesgo
de frescura. Medición: de las 1181 "resoluciones" no-deportivas, 1181 (100%) tienen
`endDate` en el FUTURO respecto a hoy, y 0 tienen `endDate` pasado. O sea: la Gamma devuelve
los `closed=true` con outcome pre-resuelto pero cierre en el futuro (resoluciones
anticipadas por cierre temprano/nominación, no eventos que transcurrieron naturalmente).

**Consecuencia:** NO hay dataset retrospectivo NATURAL (evento ocurrido con su resultado)
para backtestear edge price-vs-result. El pre-registro medía n>=200 + rate>=0.95, pero el
test de frescura (mi propia disciplina) revela que n_natural=0. El veredicto SUCCESS es
FORMAL pero OPERATIVAMENTE NO REUTILIZABLE para backtest.

**Conclusión corregida:** la vertical es RICA y CAPTURABLE (dato firme), pero el edge NO es
backtesteable retrospectivamente con la Gamma como la consulté. Para estimar edge se
requiere RECOLECCIÓN FORWARD: acumular mercado abiertos de elecciones/economía mientras se
resuelven, y medir price-vs-result sobre datos frescos que sí pasaron. Eso es recolectar en
el ciclo (como hace el bot con sports), no un snapshot retrospectivo.

**Implicación para el plan:** el "dataset suficiente" (criteria del pre-registro) no se
obtiene de un pull histórico; se obtiene corriendo un recolector forward durante el ciclo de
un evento (días/semanas). Ese es el siguiente paso si se persigue la vertical, y requiere
decisión explícita porque es trabajo continuo, no un one-shot.

## Fuente

Gamma API polymarket.com (acceso público, sin key), mismos adaptadores que el bot.
