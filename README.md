# Polymarket Vertical Research

Investigación de la **vertical no-deportiva** en Polymarket (elecciones, economía,
geoestrategia) para decidir con datos reales si es una vertical explotable — sin minar
datos ni inventar edges.

Cubre: reconocimiento del universo, medición de **capturabilidad** (libro CLOB real),
y un **recolector forward** que acumula snapshots de los mercados que resuelven pronto
para backtestear edge sobre resoluciones naturales limpias.

## Qué encontró este research

- **Riqueza por fuente** (muestra 300): Polymarket no-deportivo = 95 mercados vivos,
  US$36.7M vol24h → rica. Manifold pobre (~US$15K). Kalshi no medible (endpoints distintos).
- **Capturabilidad**: no-deportivo 20/20 mercados con libro CLOB, profundidad media 9.1M,
  spread medio 0.005 → **~17x más profundo y la mitad del spread que sports.**
- **Resolución**: la Gamma devuelve closed con outcome pre-resuelto pero endDate futuro →
  0/1181 resoluciones naturales retrospectivas. El edge NO es backtesteable con un pull
  histórico de la Gamma; requiere **recolección forward**.
- **Recolector forward ampliado**: horizonte 30d, 209 mercados (vol24h ≥ $10K),
  40 libros CLOB reales por ciclo, universo en append.

## La medición está en curso

El recolector corre cada 4h (cron de Hermes). Con 113 mercados resolviendo en ≤7 días
(Fed, Suecia, US Open, geoestrategia), la primera muestra natural limpia de edge llega
en ~1 semana. No se declara un EV hasta tener resoluciones naturales + entrada.

## Estructura

- **Scripts** (`*.py`): recolector forward, análisis de capturabilidad/riqueza/resolución,
  utilidades de inspección.
- **`pre-registro-edge-nosport.md`**: hipótesis y kill/success criteria fijados ANTES de
  ver datos (anti-minería).
- **`ESTADO.md`**: narrativa completa con todos los números medidos, artefactos
  descartados por contaminación (backtest de pmxt invalidado), y estado de la automatización.
- **`delta/`**: tablas Delta regenerables (gitignored) — corridas de los scripts.

## Stack

`deltalake` + `duckdb` + `pyarrow` (venv /tmp/lh-venv). Ingestion vía Gamma API pública
sin key, y CLOB público por token para el libro.

## Contexto más amplio

Este research es la aplicación del método destilado en el repo `hermes-skills`
(empirical-*-skills: invariants, delta-lakehouse, medallion-architecture). Las skills y el
método están en `manusabbath-arch/hermes-skills`; este repo es la evidencia empírica que las
valida.
