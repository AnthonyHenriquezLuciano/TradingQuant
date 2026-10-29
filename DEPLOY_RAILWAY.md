# Despliegue persistente de TradingQuant (Railway + Vercel)

## 1. Motor FastAPI en Railway

- Código fuente: `AnthonyHenriquezLuciano/TradingQuant`, rama `main`.
- Servicio Docker: **tradingquant-api**. Root Directory: `/apps/api`. Dockerfile ya incluido en ese directorio.
- Un único proceso Uvicorn y un worker interno para trabajos científicos; el Dockerfile respeta `PORT` de Railway.
- Volumen persistente adjunto en **`/data`**. El motor usa `/data/uploads` para CSV y `/data/numba` para cache JIT. No montar en `/app`: ocultaría el código.
- Variables de servicio: `TRADINGQUANT_DATA_DIR=/data/uploads`, `NUMBA_CACHE_DIR=/data/numba`, `TRADINGQUANT_CORS_ORIGINS=https://tradingquant-beta.vercel.app,https://tradingquant-xauusd-portafolio.vercel.app,https://tradingquant-git-main-xauusd-portafolio.vercel.app,http://localhost:3000`. Usa únicamente los orígenes que sean necesarios.
- Healthcheck: `GET /health`, que debe devolver `{"status":"ok",...}`.
- Networking: generar dominio público Railway bajo HTTPS (no inventar hostname). No habilitar réplicas múltiples porque los trabajos se guardan en memoria del proceso, no en un coordinador distribuido.
- Plan: escoger capacidad de CPU/RAM/disk suficiente para Numba y CSV de 150 MB; puede tener coste. Evitar modo sleep para ejecuciones largas.

La API actual es una **beta de investigación de un solo usuario**, sin autenticación multiusuario ni límites de uso por identidad. CORS impide determinadas llamadas web de otros orígenes pero **no protege la API frente a clientes HTTP arbitrarios**. Antes de exponerla para uso público de terceros, implementar autenticación, rate limits, cuotas, persistencia de trabajos y procesamiento con colas duraderas.

## 2. Conectar el frontend de Vercel

Proyecto Vercel: `tradingquant`, equipo `team_tRCg6eBwClsec0GwazJDYuIn`.

La opción recomendada es configurar en **Production** (y Preview si procede):

```env
NEXT_PUBLIC_API_URL=https://<dominio-confirmado-de-railway>
```

No incluir la ruta `/health`, ni un slash final, ni tokens en esa variable pública.

Una vez hecho, publicar un nuevo deployment de GitHub `main`, después de comprobar que no existe bloqueo por cuota. El frontend ahora también dispone de **Datos históricos → Conexión con motor de investigación → Guardar URL / Probar conexión**. Este método alternativo permite asociar el dominio HTTPS de Railway desde el navegador **sin otro despliegue**, y comprobar `/health`. La URL solo se almacena localmente. Cada navegador debe configurarlo por separado si no existe la variable global.

## 3. Verificaciones de aceptación

1. Railway: `GET https://<api>/health` responde HTTP 200.
2. Navegador desde `https://tradingquant-beta.vercel.app`: **Probar conexión** muestra conectado sin error CORS.
3. Subir un CSV pequeño, comprobar número de filas, reiniciar servicio y verificar que el dataset sigue disponible en `/data/uploads`.
4. Ejecutar una exploración de 10–20 combinaciones, consultar progreso y recuperar OOS y trades reales.
5. Confirmar que Datos históricos y Resultados funcionan desde la URL desplegada de Vercel.
6. En CI, comprobar tanto `npm run build` como `pytest`.

La barra de progreso y los trabajos están en memoria y **se pierden cuando se reinicia el contenedor**; esto no es alta disponibilidad. El volumen conserva los CSV, no guarda la cola o el resultado de los trabajos. Los resultados terminados se guardan en IndexedDB del navegador.

**Bloqueos externos:** crear/gestionar el proyecto Railway exige la conexión de Railway autorizada por su propietario. El proyecto de Vercel puede bloquear nuevas versiones por su límite diario de despliegues: si aparece HTTP 402, no hay que eludirlo ni afirmar que se ha publicado.
