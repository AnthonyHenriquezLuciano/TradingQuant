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


### Objetivo de optimización del Creador de Algoritmos

En **Configuración → Objetivo de optimización** puedes seleccionar entre 11 métricas: balanced, sharpe, sortino, calmar, net_profit, min_drawdown, profit_factor, expectancy, win_rate, recovery_factor y funding_pass_rate.

**Todas** las métricas afectan la puntuación con la que el motor aleatorio clasifica candidatos y el motor genético selecciona población y élites. La puntuación se calcula únicamente en **IS** y no se escoge con resultados OOS. Las estrategias devueltas conservan su puntuación y métricas IS, y se ordenan por esa puntuación.

- **Balanceado:** 2 × Sharpe − 1.5 × max(0, DD% − 30) + bonificación si PF > 1.5, limitada a cinco unidades.
- **Sharpe, Sortino, Calmar:** anualización convencional de 252 jornadas; los retornos diarios se estiman a partir de *cierres realizados*, incluyendo jornadas observadas sin cierre de operaciones. No son métricas diarias mark-to-market.
- **PnL:** USD finales menos depósito inicial. **Drawdown:** negativo del porcentaje máximo de reducción en balance realizado. **Profit Factor:** beneficios brutos realizados sobre pérdidas brutas (valor finito de protección cuando no existen pérdidas). **Expectancy:** PnL medio USD por trade. **Win rate:** porcentaje de trades ganadores. **Recovery factor:** PnL dividido por el descenso absoluto máximo del balance en USD.
- **Pass Rate Fondeo:** proxy de tasa de aprobación de evaluación de dos fases (metas 8% y 5%). En cada fase remuestrea 128 trayectorias de jornadas IS durante un máximo de 60 jornadas, con límites de pérdidas diarias y totales realizados configurados en la sesión; no exige mínimo de días. El cálculo **no reproduce** pérdidas flotantes, ejecución intrabar real, márgenes, reglas especiales de fondeadoras, calendarios futuros ni dependencia temporal real de retornos. Esta estimación no se debe presentar como una probabilidad verdadera de aprobar una cuenta de fondeo.

Los candidatos con menos operaciones IS que el mínimo configurado reciben una penalización de selección. Cada objetivo y valor aparece en el objeto de resultados junto con las métricas de validación OOS.


### Fondeo: fases, drawdown, consistencia y aprobación por tiempo

La quinta pestaña **Fondeo** guarda una configuración por sesión y puede activarse/desactivarse. Incluye presets **editables** FTMO 2-Step, FTMO Swing (plantilla), FundingPips 2-Step Standard, The5ers High Stakes, Topstep Combine 50K, FundedNext Stellar (plantilla) y Lucid Trader Flex (plantilla). Los valores predefinidos son puntos de partida: debes contrastarlos con tu contrato, tipo exacto de cuenta y fecha de la compra.

**Modelo de evaluación soportado:**
- De **1 a 3 fases**; objetivo porcentual por fase, máximo de días (horizonte de simulación), número mínimo de días, y umbral de beneficio diario para acreditar esos días. 0% significa cualquier día con al menos una **operación cerrada** (no reproduce necesariamente la definición de «trading day» de cada firma, que puede contar aperturas).
- **DD diario:** límite realizado respecto al saldo de cierre previo menos porcentaje del capital inicial, o límite realizado fijo respecto al saldo inicial. 0% desactiva el límite diario; NO hay equity flotante.
- **DD total:** estático basado en capital inicial o trailing al cierre (EOD), con opción de impedir que el piso supere el capital inicial.
- **Consistencia:** sin regla, proporción máxima del mejor día frente al beneficio total, o proporción máxima frente al target que **eleva el objetivo efectivo** (estilo Topstep).
- **Monte Carlo:** 64–1000 caminos por candidato con bootstrap por bloques de 1–20 días del tramo IS, recomenzando el balance por fase y avanzando solo si la fase previa aprueba. Reporta Pass Rate, aprobación acumulada por fase, P20/P50/P80 **condicionales a aprobar**, promedio de días exitosos, tasa **incondicional** que aprobó dentro del plazo, conteo de éxitos y fallos por DD/tiempo.
- **Filtrado temporal:** tasa mínima de aprobación (0% = medir sin descartar), percentil de días configurable y máximo de días para ese percentil (0 = ilimitado). Ambos filtros deben superarse para la aceptación. En modo mayor Pass Rate, el objetivo pondera la tasa de aprobación por velocidad: tasa/(1+días del percentil elegido/365).
- El motor hace selección en IS. Las estimaciones OOS se producen únicamente para diagnóstico y no afectan la selección genética. La vista de resultados muestra tasa OOS, P20 y probabilidad OOS dentro del plazo.

**Restricciones científicas:** Solo disponemos de PnL *realizado* al cerrar cada trade y de días de los cierres. Por tanto no es posible verificar DD intrabar/tick, límite de equity flotante, límites de margen, slippage, restricciones de noticias, tamaño máximo de posición o el día en que se abrió un trade que cerró otro día. Las tasas simuladas son **proxies**, no probabilidades de aprobación reales ni garantías de cumplimiento de las reglas de FTMO, FundingPips, Topstep u otras firmas. Algunos presets como Topstep usan trailing EOD aproximado aunque la regla oficial puede evaluar equity intradía. El proyecto necesita un feed tick/broker y un simulador basado en equity mark-to-market para reproducir los contratos por completo.


### Avanzado: entradas, modificadores y posiciones compuestas

La sexta pestaña **Avanzado** sigue el diseño negro/dorado del creador y guarda su configuración con la sesión:

- **Entradas Mercado, Stop, Limit:** pueden seleccionar varios tipos para que el generador pruebe versiones distintas de los candidatos. Mercado entra en la siguiente apertura tras el cierre de señal. Stop opera ruptura de máximo/mínimo confirmado de barras anteriores; Limit espera un retroceso medido en ATR. Ambas órdenes tienen caducidad. Ante el toque de entrada y SL en una misma vela, se asume SL primero. Las órdenes pendientes y escaladas exigen modelado OHLC, no el modo "solo apertura".
- **Ratio fijo:** reemplaza el cálculo de TP elegido en Gestión de capital, conservando la distancia inicial del stop.
- **Riesgo variable:** anti-martingala (aumenta con wins, vuelve a base al perder), martingala (aumenta con pérdidas, opcionalmente reinicia al ganar), multiplicador y niveles. El presupuesto total por posición compuesta se limita a **2% del capital de referencia**, sin permitir que las patas adicionales superen el límite al stop. NO reproduce liquidación ni uso de margen del broker.
- **Break-even avanzado:** activación en ATR, R o % del precio; offset favorable en pips con tamaño de pip explícito del instrumento. Tiene prioridad sobre BE del módulo Gestión de capital.
- **Trailing avanzado:** activación y distancia configurables, cada una en ATR, R o %; se actualiza tras el cierre de barra, priorizando este modificador sobre trailing básico.
- **DCA / Pirámide:** niveles 2–8 incluyendo entrada inicial, multiplicador de tamaño, distancia en ATR/R/%; pueden combinarse. El capital de riesgo se reserva inicialmente para TODAS las posibles patas, por lo que el lote inicial puede ser menor. Con SL/TP desde el promedio ponderado, el stop **solo se puede acercar** a la posición, nunca alejar, evitando exceder el riesgo reservado.

**Convenciones científicas:** sólo hay datos OHLC. Se comprueba el SL de la posición existente antes que nuevos fills DCA/pirámide. Si las dos escaleras son tocadas en una misma vela, se prioriza una sola pata DCA para no inventar la secuencia temporal. Las protecciones avanzadas sólo afectan a la siguiente vela tras confirmarse el cierre. Las operaciones compuestas se contabilizan como una única operación para las restricciones diarias. El motor no simula latencia, slippage variable, tasas de swap, liquidaciones, garantía de llenado, niveles reales de margen, profundidad de libro ni spread variable, por lo que las métricas no equivalen a una validación con tick real. En pruebas IS/OOS se utiliza el mismo modificador y modo de entrada del candidato, sin optimizar decisiones usando el futuro.


### Últimos controles de investigación: Filtro, Walk-Forward, Multiverso, Costes

Se incorporaron cuatro pestañas adicionales al laboratorio de algoritmos, con configuración persistida por sesión:

**Filtro** — Sharpe diario anualizado sobre resultados realizados (252 días), drawdown máximo, win rate mínimo, DSR estimado y operaciones mínimas/máximas por periodo. Se filtran candidatos con datos **IS antes de crear la shortlist**; se vuelven a comprobar umbrales en OOS para reportar validación. El DSR corrige aproximadamente el Sharpe por distribución no normal y por la cantidad de candidatos realmente explorados en **este mercado**, utilizando asimetría, curtosis, días observados y la esperanza del máximo entre múltiples intentos. No es una prueba de independencia estadística de todas las estrategias, ni controla todas las formas de selección.

**Walk-Forward** — ventanas OOS cronológicas sin solapamiento; tamaños 1/12 a 1/2 del tramo de validación; evaluación pura con parámetros congelados y modo de **re-selección de candidatos**, que sólo usa información disponible antes de cada ventana. La re-selección emplea el pool generado en IS: NO realiza nueva evolución genética ni recalibra libremente indicadores nuevos en cada ventana. Reporta WFE, Sharpe OOS y porcentaje de ventanas aprobadas y permite rechazar candidatos. La ratio WFE se aproxima por rendimiento porcentual realizado por día en ventana dividido por rendimiento porcentual IS por día, siempre que este último sea positivo. El tramo inicial OOS sirve como nueva información disponible para las siguientes ventanas sólo en el modo re-selección. Esto no garantiza rendimiento externo independiente tras la adaptación.

**Multiverso** — genera de 50 a 1000 series OHLC sintéticas con continuidad de precios positivos a partir de exclusivamente el conjunto IS; bootstrap por bloques de distintas longitudes y escenarios de shocks. Cada estrategia **recalcula sus señales** en cada serie, ejecuta su mismo motor de salida/gestión, y agrega supervivencia, P95 de DD, esperanza mediana y score de hechos estilizados (colas, volatilidad y autocorrelación de |retornos|). El HMM gaussiano (estimado por Baum–Welch) proporciona una descripción exploratoria de 1–3 regímenes de volatilidad del histórico IS, no una clasificación económica verdadera ni una garantía de que todos los universos reproduzcan esos regímenes. Para controlar carga, se utiliza como máximo una ventana histórica de 6000 barras por candidato y hasta 10 candidatos. La ejecución es síncrona en el motor actual y puede requerir recursos importantes; no se ejecuta en segundo plano.

**Costes** — catálogo editable por instrumento con spread en pips, comisión ida/vuelta por lote, slippage, swap L/S, tamaño de pip, contrato, conversión a USD y días **estimados** de financiación. Cuando se activa "Aplicar al backtest", convierte esos importes a bps redondos respecto al nocional empleando exclusivamente un precio de referencia en IS para cada timeframe; el valor se congela para la evaluación OOS. No recalcula tarifas ni swaps exactos por cada trade; el spread es fijo y el slippage es una estimación. Sin especificación confiable, dejar desactivado y utilizar el coste genérico bps. Las cifras del catálogo genérico son **ilustrativas** y no provienen de ningún broker. La importación automática de especificaciones desde **MT5 queda indicada como "Próximamente"** y no hay conexión operativa con MT5.

#### Limitaciones comunes
Todas las operaciones siguen el simulador OHLC actual. No se afirma que datos sintéticos, DSR, WFE, IS/OOS, o una estimación de coste puedan sustituir forward testing, ticks reales, microestructura, disponibilidad de liquidez, especificaciones actuales de broker o drawdown flotante. En el frontend Vercel, el configurador y las vistas funcionan, pero la API Python FastAPI aún requiere un despliegue público y conexión antes de poder iniciar simulaciones científicas desde la web.


### Nueva exploración real, diagnóstico ATR y panel de resultados auditables

FastAPI incorpora POST /api/explorations/preflight, POST /api/explorations/start, GET /api/explorations/jobs/{id} y GET /api/explorations/jobs/{id}/result. El diagnóstico preflight obtiene P5/P25/mediana/P75/P95 del ATR(14) desde el CSV y el periodo seleccionados, además de muestras de frecuencia de señales por día. Los resultados son descriptivos y NO límites universales del indicador. Informa cuando dos límites pueden ser redundantes o cuando la muestra indica un máximo diario de señales por debajo del límite configurado.

El motor ejecuta una cola de un worker con hasta dos trabajos activos o pendientes, informando fase, progreso, número evaluado y tiempo transcurrido directamente desde el cálculo real. Una ejecución terminada devuelve hasta 50 estrategias con score IS, evaluación OOS y trazas generadas por el mismo motor Numba utilizado en el backtest. El nuevo detalle muestra precios y tiempos reales de entrada y salida, R por operación, balance OOS, curva equity, OHLC histórico, costes agregados, rendimiento mensual, calendario, ranking filtrable y simulación de fondeo por fases. El botón Guardar en Mis Algoritmos queda deshabilitado (Próximamente).

Los resultados del navegador se almacenan en IndexedDB, evitando exceder fácilmente la cuota limitada de localStorage. No hay sincronización entre equipos ni guardado central por usuario. Los trabajos y su cola permanecen en memoria de un único proceso Python y se perderían al reiniciarse; falta cola duradera para alta disponibilidad.

Se eliminaron controles duplicados e inertes de ratio TP/SL, ATR, riesgo y DD de la sección Configuración. Gestión de capital concentra el riesgo operativo, sizing y SL/TP; Avanzado modifica su comportamiento; Costes gestiona coste genérico y catálogo; Fondeo simula las evaluaciones de cuentas y Filtro establece umbrales de aceptación independientes de las reglas de ejecución. Sólo los indicadores marcados como habilitados tienen motor de señales; el resto del catálogo técnico y las series macro son futuribles.

El Dockerfile del motor se incluye en apps/api/Dockerfile y docker-compose.yml crea un volumen de CSV y Numba, con puerto enlazado a localhost para evitar una API abierta sin autenticación. Para conectar Vercel se requiere un host persistente HTTPS para FastAPI, configurar TRADINGQUANT_CORS_ORIGINS y la variable NEXT_PUBLIC_API_URL apuntando a dicho host. La web publicada no puede ejecutar las simulaciones si no existe ese backend público. La sincronización MT5 sigue sin implementarse.

Alcance: los resultados son OHLC u open-bar, no ejecución tick real; tampoco hay garantía de rentabilidad ni equivalencia total a StrategyQuant. La evaluación histórica OOS, el bootstrap, las ventanas Walk-Forward y Multiverso son pruebas experimentales y deben contrastarse con forward testing.

## Despliegue del motor científico en Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AnthonyHenriquezLuciano/TradingQuant)

El archivo [`render.yaml`](./render.yaml) prepara **un servicio Docker de pago de 2 GB de RAM y un disco persistente de 5 GB**. **Revisa y aprueba el coste en Render** antes de crearlo; el botón no despliega ni factura sin tu confirmación. Un servicio Free no serviría para conservar los CSV en disco. El proceso de análisis permanece en memoria y se interrumpirá si reinicias la instancia. Al terminar, copia la URL HTTPS y configúrala en *TradingQuant → Datos históricos → Conexión con motor de investigación → Guardar URL → Probar conexión*, o utiliza la variable `NEXT_PUBLIC_API_URL` en Vercel.

**Seguridad:** el Blueprint configura `TRADINGQUANT_REQUIRE_AUTH=1` y crea un `TRADINGQUANT_ACCESS_TOKEN` aleatorio en Render. En el dashboard de Render copia/revela ese secreto y guárdalo en **TradingQuant → Datos históricos → Token privado → Guardar token en esta sesión**. Después pulsa **Probar conexión**: se verifica `/health` y `/api/auth/check`. El token se guarda únicamente en `sessionStorage` del navegador (no en `NEXT_PUBLIC_*` ni en GitHub). Es autenticación compartida de un solo usuario, **no** gestión de usuarios, cuotas ni cola distribuida; no publicarlo como plataforma multiusuario sin esas protecciones.
