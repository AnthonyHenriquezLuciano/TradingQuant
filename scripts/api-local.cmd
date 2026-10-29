@echo off
title TradingQuant - API local FastAPI
cd /d "%~dp0..\apps\api"
set "TRADINGQUANT_REQUIRE_AUTH=0"
set "TRADINGQUANT_LOCAL_MODE=1"
set "TRADINGQUANT_MAX_UPLOAD_MB=1024"
set "TRADINGQUANT_DATA_DIR=%CD%\data\uploads"
set "NUMBA_CACHE_DIR=%CD%\data\numba"
set "TRADINGQUANT_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000"
if not exist "%TRADINGQUANT_DATA_DIR%" mkdir "%TRADINGQUANT_DATA_DIR%"
if not exist "%NUMBA_CACHE_DIR%" mkdir "%NUMBA_CACHE_DIR%"
if not exist "%CD%\data\inbox" mkdir "%CD%\data\inbox"
echo Motor cientifico: http://127.0.0.1:8000
echo API disponible solo desde esta computadora.
".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
echo.
echo La API se cerro. Revisa el mensaje anterior.
pause
