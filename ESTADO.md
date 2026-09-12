# Estado del programa de exploración vertical no-deportiva

Fecha del snapshot final: 2026-09-12

## Qué se probó y qué se midió (datos reales, no estimaciones)

### 1. Riqueza por fuente (bronze_verticales)
- Polymarket no-deportivo: 95 mercados vivos, US$36.7M vol24h → RICA
- Manifold: 100 mercados, US$15K → POBRE (descartar)
- Kalshi: 100 mercados, sin campo de volumen uniforme → no medible, descartar como fuente primaria

### 2. Capturabilidad (bronze_capturabilidad + gold)
- No-deportivo: 20/20 mercados con book CLOB, profundidad media 9.1M, spread medio 0.005
- Comparación sports: profundidad 0.5M, spread 0.01
- Conclusión: no-deportivo es ~17x más profundo y ~la mitad del spread → MÁS capturable que sports

### 3. Resolución (bronze_resoluciones) — con pre-registro [pre-registro-edge-nosport.md]
- 1,200 mercados cerrados: 1,181 no-deportivos, 1,181 resueltos (rate 100%)
- Veredicto FORMAL del pre-registro: SUCCESS (n=1181 >= 200, rate=100% >= 0.95)

## HALLAZGO CRÍTICO DE FRESCURA (enmienda al pre-registro)
- De las 1181 "resoluciones", 1181 (100%) tienen endDate FUTURO vs hoy, 0 pasado.
- La Gamma devuelve closed=true con outcome pre-resuelto pero cierre en futuro →
  resoluciones ANTICIPADAS (cierre temprano), no eventos transcurridos naturalmente.
- → NO hay dataset retrospectivo natural para backtestear edge price-vs-result (n_natural=0).
- El SUCCESS es FORMAL pero OPERATIVAMENTE NO REUTILIZABLE para backtest.

## Conclusión estratégica
- La vertical es RICA y CAPTURABLE (dato firme).
- El EDGE no es backtesteable retrospectivamente con la Gamma como la consulté.
- Para estimar edge: RECOLECCIÓN FORWARD (acumular mercados abiertos mientras se resuelven,
  medir price-vs-result sobre datos que sí pasaron) — como hace el bot con sports.
- Es trabajo CONTINUO (días/semanas de ciclo), no un one-shot. Requiere decisión explícita
  del usuario antes de montarlo.

## Artefactos en /home/mamba/vertical-exploration/
- delta/bronze_verticales, bronze_capturabilidad, bronze_resoluciones
- delta/gold_riqueza_vertical, gold_capturabilidad_vertical, gold_frescura_resolucion
- pre-registro-edge-nosport.md (con enmienda de frescura)
- analizar_bronze.py, capturabilidad.py, analizar_capturabilidad.py
- recolectar_resoluciones.py, verificar_pre_registro.py, verificar_frescura.py

## Ampliación de muestra (2026-09-12)

Siguiendo el pedido de muestra amplia, amplié el recolector forward:

- **Horizonte**: 14 → **30 días**. Universo pasó de 29 a **~209 mercados** no-deportivos vivos
  con token y vol24h ≥ $10K (filtro de liquidez; los que concentran U$31.7M del volumen).
- **Universo**: se guarda ahora en **append** (creciente entre ciclos, dedup por market_id).
- **Snapshots por ciclo**: 15 → **40** books reales del CLOB por ciclo (rate-limited).
- **Cobertura ampliada confirmada**: 207 mercados únicos trackeados, 85 snapshots acumulados,
  53 ciclos. Distribución: ≤7d = 113 mercados (U$27.9M), ≤30d = 85 (U$3.9M), ≤14d = 9.
- **Temas cubiertos**: elecciones (29), Irán (15), presidente (13), Brasil (12), Fed (8),
  US Open (8), Suecia (8), Hormuz (6), PM (5). Nuevas categorías geoestrategia (ej. Kharg
  Island US$7M de profundidad) entraron al tracking.

El recolector ampliado está en `recolector_forward.py` (HORIZON_DAYS=30, MIN_VOL24H=10k,
TOP_SNAPSHOT=40). El cron `recolector-forward-nosport` (539d700f88f4) sigue igual; se
beneficia de la ampliación automáticamente.

**Nota de costo**: ahora cada ciclo hace ~40 llamadas al CLOB (antes 15). A cadencia 4h
(~6 ciclos/día) son ~240 queries/día al CLOB de Polymarket — moderado, pero hay que vigilar
rate limit. Si aparece throttling, bajar TOP_SNAPSHOT. `--all` sube a 80.

## Nota: no se tocó research/registry.json del bot
El checkout del bot está en una rama de auditoría compartida con sesiones paralelas vivas
(2 procesos claude). Por la convención del repositorio, no se modificó el registry del bot.
El pre-registro vive en el workdir standalone por ahora. Promover a registry.json del bot
requiere un worktree dedicado y limpiar las sesiones paralelas.

## Avance: recolector forward operativo (2026-09-12)

Se construyó y validó el "medir sin esperar" — recolección forward acotada a mercados de
resolución cercana (≤14 días), que acumula snapshots del book CLOB real por ciclo.

**Qué resuelve:** el bloqueo de frescura (los eventos no-deportivos largos, elecciones 2028,
no tienen resolución natural retrospectiva vía Gamma ni datasets gratis ligeros — confirmado
Gamma 0/1181, manja316 0/9550). En lugar de esperar años o bajar 36GiB (no cabe: 22G libres),
se capturan los mercados que SÍ resuelven pronto y se registra su entrada mientras se
resuelven.

**Lo que ya queda capturando (validado, libro CLOB real por token):**
- 29 mercados vivos de no-deportivo con endDate en ≤14d, top por volumen.
- `recolector_forward.py` captura cada ciclo el book (bid/ask/spread/profundidad) y hace
  append a `delta/forward_snapshots`. 28 ciclos acumulados = 45 snapshots (dedup por ts).
- 15/15 consultados con book real, sin error.
- Profundidades de la vertical confirmadas de nuevo (reales, no estimación): Fed US$34M
  (2.5bps) / US$27M / US$26M, Zverev US Open US$21M, Fed no-change US$5M.

**Cómo se automatizó:**
- Cron `recolector-forward-nosport` (job 539d700f88f4), cada 4h, `no_agent` sobre wrapper
  `~/.hermes/scripts/recolector_forward_watch.sh`. **⚠️ El gateway de Hermes NO está
  corriendo** — el job está creado y activo pero NO ejecuta hasta `hermes gateway start`.
  Hasta entonces, correr `bash ~/.hermes/scripts/recolector_forward_watch.sh` a mano (o vía
  otro cron del sistema).

**Timeline de medición del edge (sin contaminación):**
- Fed September resuelve en **4 días** → primera resolución natural real capturada con su
  serie de entrada → se puede evaluar entry-vs-resultado sobre muestra imparcial.
- Geo (Hormuz), Suecia (1-2d), US Open (1-6d) también resuelven pronto → varias resoluciones
  en la primera semana.
- Con ~10+ resoluciones naturales con entrada + resultado, recién ahí se puede afirmar (o
  no) un EV. Hoy NO hay edge que declarar: hay canal de medición y blancos.

**Scripts en el workdir:**
- `recolector_forward.py` — recolector principal (select mercados ≤14d + snapshot CLOB + append).
- `listar_14d.py`, `estado_snapshots.py` — utilidades de inspección.
- `backtest_resolved.py` / `backtest_edge.py` — **DESCARTADOS por contaminación**
  (fetch_trades de pmxt devolvió la misma serie para tokens distintos; el EV/un 150+
  es numéricamente imposible para un binario). No usar. Documentado para no reincidir.
- `ESTADO.md` — este resumen.
