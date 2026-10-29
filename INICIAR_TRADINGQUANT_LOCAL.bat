@echo off
setlocal EnableExtensions
title TradingQuant - Instalacion e inicio local
cd /d "%~dp0"
echo.
echo ================================================
echo       TRADINGQUANT - MODO LOCAL WINDOWS
echo ================================================
echo.
where npm >nul 2>nul
if errorlevel 1 (
 echo ERROR: Instala Node.js LTS y reinicia esta ventana.
 echo Descarga oficial: https://nodejs.org/
 pause
 exit /b 1
)
py -3.12 --version >nul 2>nul
if errorlevel 1 (
 echo ERROR: Se requiere Python 3.12 con el lanzador py.
 echo Descarga oficial: https://www.python.org/downloads/
 echo Activa "Python launcher" durante la instalacion.
 pause
 exit /b 1
)
if not exist "apps\api\.venv\Scripts\python.exe" (
 echo [1/4] Preparando entorno de Python 3.12...
 py -3.12 -m venv "apps\api\.venv"
 if errorlevel 1 goto failed
)
if not exist "apps\api\.venv\.tradingquant-deps-ready" (
 echo [2/4] Instalando bibliotecas cientificas...
 "apps\api\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "apps\api\requirements.txt"
 if errorlevel 1 goto failed
 echo ready>"apps\api\.venv\.tradingquant-deps-ready"
)
echo [MT5] Verificando conexion Python con MetaTrader 5...
"apps\api\.venv\Scripts\python.exe" -c "import MetaTrader5" >nul 2>nul
if errorlevel 1 (
 echo Instalando integracion oficial MetaTrader5 para Windows...
 "apps\api\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check MetaTrader5
 if errorlevel 1 (
   echo ERROR: No se pudo instalar MetaTrader5. Verifica Windows 64 bits y Python 3.12.
   goto failed
 )
)
if not exist "apps\web\node_modules\next" (
 echo [3/4] Instalando dependencias del frontend...
 pushd "apps\web"
 if exist "package-lock.json" (
   call npm ci
 ) else (
   call npm install
 )
 if errorlevel 1 (
   popd
   goto failed
 )
 popd
)
echo [4/4] Iniciando API y pagina local...
start "TradingQuant - Motor Cientifico" cmd /k call "%~dp0scripts\api-local.cmd"
start "TradingQuant - Interfaz Web" cmd /k call "%~dp0scripts\web-local.cmd"
echo.
echo La pagina se abrira en http://127.0.0.1:3000
echo La API local estara en http://127.0.0.1:8000/health
echo Mantener abiertas ambas ventanas durante el trabajo.
echo Render y Vercel no son necesarios en este modo.
echo.
echo Si la instalacion fallo, revisa los mensajes de esta ventana.
pause
exit /b 0
:failed
echo.
echo ERROR: No se pudo completar la instalacion.
echo Comprueba tu conexion y vuelve a ejecutar este archivo.
pause
exit /b 1
