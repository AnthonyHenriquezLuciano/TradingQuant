# TradingQuant — Modo local Windows

El modo local ejecuta Next.js (interfaz) y FastAPI (motor) en una misma computadora, sin depender de Render ni de Vercel. Todo está restringido a 127.0.0.1: no se ejecutan órdenes reales.

## Requisitos

Windows 10/11, Node.js LTS con npm, Python 3.12 (64 bits) con el lanzador py, Git y conexión a Internet para la instalación inicial. Se recomiendan 16 GB de RAM o más y SSD; con 8 GB se puede comenzar con pruebas pequeñas.

## Un solo clic

1. Descarga el repositorio ZIP de GitHub (Code → Download ZIP), o clónalo con Git.
2. Descomprime en una carpeta, por ejemplo C:\TradingQuant.
3. Haz doble clic en el archivo INICIAR_TRADINGQUANT_LOCAL.bat en la raíz.
4. En el primer inicio, el script prepara el entorno virtual de Python, instala bibliotecas científicas y dependencias de Next.js.
5. Mantén abiertas las dos ventanas nuevas (Motor Científico y Web).
6. Abre http://127.0.0.1:3000 y visita Datos históricos. Configura la URL http://127.0.0.1:8000 y pulsa Probar conexión. **No se necesita token en modo local.**
7. Sube tu CSV original de MetaTrader 5 y crea una exploración.

La página publica de Vercel es distinta a la página local. Para trabajar sin Render hay que abrir http://127.0.0.1:3000.

## Archivos e investigación

Los CSV se guardan en apps/api/data/uploads, la caché Numba en apps/api/data/numba y los resultados de sesión se guardan en el navegador local. No se sincronizan automáticamente con los datos de la web pública. El límite de CSV local es de 1024 MiB y se ajusta en scripts/api-local.cmd con TRADINGQUANT_MAX_UPLOAD_MB. No es una garantía de poder ejecutar backtests de archivos tan grandes con cualquier equipo: el motor también necesita memoria para sus estructuras de cálculo.

El primer arranque requiere Internet para instalar dependencias. Después, el modo local puede funcionar sin Internet en operaciones que solo usan archivos ya importados. Si se actualizan los requisitos Python, elimina apps/api/.venv/.tradingquant-deps-ready y vuelve a ejecutar el iniciador; para dependencias de Next.js, npm ci en apps/web.

## Seguridad

FastAPI escucha solo en 127.0.0.1:8000. TRADINGQUANT_REQUIRE_AUTH=0 solo debe usarse cuando el servicio permanezca local; no cambies host a 0.0.0.0 sin autenticación y controles de acceso. La copia local de los CSV no está protegida por cifrado adicional. Para acceder desde móvil u otros equipos, necesitarás un mecanismo seguro y autenticado distinto del modo local simple.

## Diagnóstico

- No reconoce py -3.12: instala Python 3.12 con el Python Launcher.
- No reconoce npm: instala Node.js LTS y reabre la consola.
- Puerto 8000/3000 ocupado: cierra la instancia anterior.
- No se conecta: revisa http://127.0.0.1:8000/health y los errores en la ventana de Python.
- Está apuntando a Render: abre http://127.0.0.1:3000 y corrige la URL del motor en Datos históricos.
- CSV inválido: confirma el formato MT5 con columnas DATE, TIME, OPEN, HIGH, LOW, CLOSE y al menos 300 filas válidas.

Para ejecución manual, lee los comandos en el README principal y utiliza Python 3.12.
