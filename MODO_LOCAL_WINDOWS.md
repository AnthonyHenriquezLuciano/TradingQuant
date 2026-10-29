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

## Primer inicio obligatorio con MetaTrader 5

1. Instala MetaTrader 5 de tu bróker o empresa de fondeo en Windows y **abre sesión desde el propio terminal**.
2. Ejecuta **INICIAR_TRADINGQUANT_LOCAL.bat**. Ahora instala, además, el módulo oficial `MetaTrader5` de Python 3.12 para Windows. **No** necesitas instalar el módulo en Render.
3. Abre **http://127.0.0.1:3000**. En el menú **Principal → Cuentas** selecciona **Nueva cuenta**, indica un nombre, el tipo (fondeo/real/demo), fase, reglas de DD y, opcionalmente, la ruta de `terminal64.exe`.
4. TradingQuant se conectará **sin contraseña** al terminal ya autenticado, mostrará el login, servidor y bróker y desbloqueará el laboratorio.
5. Puedes registrar varias cuentas desde diferentes instalaciones locales de MT5, cada una con su ruta a `terminal64.exe`. **Solo una conexión activa por proceso Python**: al cambiar de cuenta se verifica que el terminal abierto coincida con el login y servidor guardados.
6. En Creador de algoritmos, el selector **Símbolo** proviene del inventario `symbols_get()` de la cuenta activa; puedes importar velas de MT5 usando el intervalo de fechas seleccionado (90 días M1 si dejas el campo de fechas vacío).
7. En **Costes**, el terminal aporta spread actual, tamaño y valor del tick, tamaño de contrato, lotaje y swaps. **No se garantiza obtener comisiones por lote ni slippage históricos** a través de `symbol_info`; completa los valores no disponibles antes de activar el catálogo de costes.

**Requisitos y límites:** Windows con terminal MT5 abierto y autenticado, Python 3.12 de 64 bits; `MetaTrader5` no funciona como reemplazo de un terminal en la nube. El historial es el disponible en MT5 y está sujeto a su parámetro *Tools → Options → Charts → Max. bars in chart*. Las barras y ticks de MT5 se interpretan en UTC. No hay envío de órdenes (`order_send` no se utiliza) y no se almacenan contraseñas en GitHub ni en el disco de TradingQuant.

## Indicadores y transparencia de datos

El generador actualmente tiene **59 familias de señales implementadas y ejecutables** (9 originales y 50 nuevas basadas en OHLC). Los otros elementos del catálogo, especialmente macroeconómicos, profundidad, Delta/CVD y perfiles de volumen, permanecerán deshabilitados hasta contar con datos y fórmulas verificables; no se presentan como estadísticas reales indicadores que requieren fuentes adicionales. Las pruebas automáticas comprueban que las señales técnicas no emplean velas futuras.

## Importación directa sin subir por el navegador

Para CSV M1 de varios años puedes evitar por completo la transferencia HTTP:

1. Copia el archivo CSV original de MetaTrader 5 a **apps/api/data/inbox/** (el iniciador crea la carpeta automáticamente).
2. Abre **http://127.0.0.1:3000** → **Datos históricos**.
3. En **Importación directa desde el disco**, pulsa **Buscar archivos CSV locales**.
4. Selecciona el archivo y pulsa **Importar del disco**. La API crea una referencia/copia local y valida filas en segundo plano.
5. El dataset aparece disponible en el Creador de Algoritmos.

La aplicación local utiliza siempre **http://127.0.0.1:8000**. No hay campo de token, URL de Render ni integración requerida con Vercel. Puedes apagar los servicios en la nube sin afectar tus investigaciones locales. No borres la carpeta **apps/api/data/** si quieres conservar tus datos.

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
