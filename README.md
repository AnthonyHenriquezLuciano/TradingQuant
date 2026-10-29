# TradingQuant

Laboratorio de investigación cuantitativa y creador de algoritmos con enfoque en validación fuera de muestra y cuentas de fondeo.

## Stack
- **Frontend:** Next.js (App Router), React, TypeScript, CSS.
- **API científica:** Python, FastAPI, Polars, NumPy y Numba.
- **Persistencia preparada:** PostgreSQL / Supabase (migración SQL con políticas RLS; conexión pendiente).
- **Estado actual:** fase 1 funcional. Exploraciones locales sobre CSV; NO conecta brókers ni ejecuta órdenes.

## Arranque

### Web
```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```
En http://localhost:3000.

### API
```bash
cd apps/api
python -m venv .venv
# activar entorno virtual
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API Docs: http://localhost:8000/docs

La web usa `NEXT_PUBLIC_API_URL=http://localhost:8000`. Para probar la interfaz sin API, puedes explorar la navegación y configurar un borrador; para subir datos y ejecutar exploraciones debes iniciar FastAPI.

## CSV admitido
Archivos OHLC con cabeceras `timestamp,open,high,low,close[,volume]` o `date,time,open,high,low,close[,volume]`. Datos ordenados cronológicamente, M1 o superiores, zona horaria original del archivo. Los costes se representan mediante un modelo inicial por puntos básicos, **no** con ticks reales, swaps ni comisión real de bróker.

## Investigación
1. Importa CSV al panel **Datos históricos**.
2. Entra a **Creador de Algoritmos**, crea una sesión y abre las dos pestañas **Configuración** (símbolo, intervalos, fechas, depósito, tipo, modelado, dirección, sizing, Multi-TF, combinaciones, datos y parámetros científicos avanzados) e **Indicadores** (familias EMA/RSI/Breakout y sus rangos configurables).
3. Configura una exploración aleatoria o una evolución genética con crossover, mutación y selección por Sharpe IS, y ejecuta la búsqueda.
4. Consulta métricas IS/OOS y bootstrap de Monte Carlo exploratorio. Los resultados pasan validaciones mínimas; no son garantías de rentabilidad.

### Limitaciones explícitas
- **Configuración disponible:** intervalos M1, M5, M15, M30, H1, H4 y D1, período inclusivo, depósito inicial en USD, modelos de aperturas y OHLC, estrategias Long / Short por separado, sizing compuesto o fijo, Multi-TF individual/combinado/ambos y un límite global de 2,000 evaluaciones.
- **Genético:** población con crossover, mutación, elitismo y Sharpe estimado desde retornos R en días con operaciones. No es Sharpe mark-to-market ni garantiza que la curva OOS sea robusta.
- **Multi-TF:** el filtro EMA20/50 del contexto HTF sólo está disponible tras cerrar completamente la vela superior. Se estudia individualmente cada TF o un par menor/mayor, no todas las permutaciones de 3+ temporalidades.
- **OHLC M1 y tick real:** visibles pero deshabilitados hasta disponer de una fuente autorizada y replay de alta resolución. No hay descarga automática de ticks; la cantidad de datos dependerá del proveedor.
- **Indicadores y situaciones (catálogo):** buscador por categoría, tabla con rangos **Desde / Pasos / Hasta** y activación por sesión. Los rangos disponibles son EMA rápida/lenta, RSI periodo/sobreventa, Breakout y umbral en puntos básicos independiente para cada barrida.
- **Barridas realmente modeladas:** máximo/mínimo de sesión de Londres (08:00–16:00 Europe/London), Asia/Tokio (09:00–17:00 Asia/Tokyo) y máximo/mínimo del último día completo disponible (PDH/PDL). En sesiones, las señales empiezan **después** del cierre de la sesión y vencen a medianoche local; ruptura por mecha + cierre dentro del rango, entrada en la siguiente vela. Seleccionar la zona horaria original del CSV. Requiere M1–H1.
- **Indicadores en desarrollo:** ADX, Bollinger, MACD, MA/SMA, EMA200, SuperTrend, VWAP, etc., aparecen en el buscador pero NO pueden seleccionarse para ejecutar hasta implementar su motor.
- **Pendientes:** jobs en segundo plano, walk-forward rodante, trading en vivo, conectores M1/tick y costes dinámicos del bróker.
- **Producción Vercel:** el frontend está conectado a GitHub y desplegado, pero FastAPI aún no está publicado y los datos/resultados no están sincronizados mediante Supabase.
- Las métricas de monte carlo son remuestreo de trades OOS, **no** una simulación completa de mercados alternativos.
- Se requiere más datos, validación independiente y modelo de costes realista antes de operar capital.
- PostgreSQL/Supabase incluyen un esquema inicial no aplicado automáticamente a ningún proyecto.

## Pruebas
```bash
cd apps/api
python -m pytest -q
```


### Catálogo de indicadores y macroeconomía (fase actual)

El Creador de Algoritmos ofrece las pestañas **Configuración** e **Indicadores**. Dentro de Indicadores, el catálogo se organiza en:

- **Técnicos:** familias EMA, RSI y Donchian implementadas; el resto de indicadores del catálogo se identifican expresamente como «En desarrollo».
- **Situaciones de mercado:** barridas de Londres, Tokio y PDH/PDL implementadas. El resto de escenarios (FVG, BOS, VWAP/POC, divergencias, apertura NY, etc.) aparece como referencia hasta que su motor esté disponible.
- **Indicadores macroeconómicos:** grupos de volatilidad/riesgo, tipos de EE. UU., tipos internacionales, dólar/FX, inflación, empleo, actividad, liquidez, materias primas, sentimiento y derivados. La interfaz permite seleccionar series y preparar una regla (subida/bajada vs observación previa o umbral, más retardo mínimo). **No hay ingesta macro histórica conectada y esas reglas no se ejecutan.** Una sesión con reglas macro seleccionadas bloquea el backtest, tanto en la UI como en FastAPI, para evitar ignorarlas silenciosamente.

La futura implementación de series macro debe conservar **vintage y observaciones históricas tal como se conocían entonces**, fecha real de publicación, revisiones, calendario, hora/zona y latencia. Una serie revisada actual no sirve para un backtest point-in-time sin controles adicionales.


### Gestión de capital: salidas y límites

La tercera pestaña, **Gestión de capital**, permite explorar tres motores implementados:

- **ATR ligado:** SL_distancia = ATR_anterior × SL_multiplicador; TP_distancia = SL_distancia × TP_multiplicador. Ejemplo: ATR 10, SL×1.5 y TP×2 ⇒ SL 15, TP 30 unidades.
- **ATR independiente:** SL_distancia = ATR_anterior × A; TP_distancia = ATR_anterior × B.
- **Porcentaje:** SL_distancia = precio_entrada × porcentaje/100; TP_distancia = SL_distancia × multiplicador_TP.

Cada parámetro de SL/TP se configura con **Desde / Pasos / Hasta** y participa en la búsqueda aleatoria o genética. Los parámetros seleccionados usando el tramo IS permanecen sin cambios al evaluar el tramo OOS. Se modelan también breakeven tras cierre de vela, trailing ATR tras cierre de vela, salida por número de barras, cooldown, máximo de trades por día, bloqueo por pérdida realizada diaria o total y beneficio realizado diario. Los modos por pips (sin información confiable del símbolo), pivote de swing, TP parcial y ATR adaptativo permanecen marcados **En desarrollo**, en lugar de simularse como si estuvieran implementados.

**Advertencias:** el motor trabaja con OHLC y costes básicos; al tocar simultáneamente SL y TP dentro de una barra, asume SL primero. Los límites de balance no modelan drawdown flotante, spread/slippage variable, liquidaciones de broker o reglas exactas de cada firma de fondeo. La API científica FastAPI y su almacenamiento aún no están publicados como servicio conectado a la web de Vercel. La visualización es funcional como configurador, pero no habilita backtesting de producción hasta desplegar la API.


### Horarios y gestión de riesgo por periodo

La cuarta pestaña **Horarios** incluye 24 horas, Sydney, Tokio, Londres, Nueva York, overlaps Tokio–Londres y Londres–NY y sesión asiática. La línea temporal y el motor utilizan los mismos intervalos **UTC fijos**. Las etiquetas de sesiones no cambian automáticamente con el horario de verano: la conversión del reloj original del CSV se realiza con la zona IANA configurada en la pestaña Horarios, pero las ventanas de negociación son las horas UTC mostradas.

Se aplican filtros de apertura para ventanas seleccionadas, viernes, primera hora del lunes y rollover 20:55–21:10 UTC, además de cierres forzados desde las 20:00 UTC diariamente (si se activa NY close) y desde las 19:00 UTC del viernes (si se activa cierre semanal). Un cierre forzado se ejecuta en la **primera apertura disponible** desde el corte, no se inventan cotizaciones. La selección de una sesión, por sí sola, **no** liquida posiciones fuera de su horario.

La pestaña **Gestión de capital** permite seleccionar límites de beneficios y pérdidas realizados diarios, semanales, mensuales y acumulados de cuenta; umbrales de rachas de wins/losses; ratio mínimo recompensa/riesgo; riesgo por trade y operaciones máximas al día. Los límites de racha detienen nuevas entradas hasta la jornada siguiente. Los límites se calculan con saldo realizado y se reinician en cortes UTC diarios/semanales/mensuales, salvo límites acumulados de cuenta. No son un sustituto de las reglas exactas de equity flotante o drawdown intradía de FundingPips ni otras firmas. Los límites se evalúan en entrenamiento y fuera de muestra.
