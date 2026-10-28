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
