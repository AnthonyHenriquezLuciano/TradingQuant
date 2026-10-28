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
2. Entra a **Creador de Algoritmos** y configura activo, temporalidad, motor aleatorio, condiciones y riesgo.
3. Ejecuta una búsqueda (sólo motor aleatorio implementado en esta fase).
4. Consulta métricas IS/OOS y bootstrap de Monte Carlo exploratorio. Los resultados pasan validaciones mínimas; no son garantías de rentabilidad.

### Limitaciones explícitas
- El motor genético, jobs en segundo plano, walk-forward rodante y pruebas de costes avanzadas están planificados; no se presentan como implementados.
- Las métricas de monte carlo son remuestreo de trades OOS, **no** una simulación completa de mercados alternativos.
- Se requiere más datos, validación independiente y modelo de costes realista antes de operar capital.
- PostgreSQL/Supabase incluyen un esquema inicial no aplicado automáticamente a ningún proyecto.

## Pruebas
```bash
cd apps/api
python -m pytest -q
```
