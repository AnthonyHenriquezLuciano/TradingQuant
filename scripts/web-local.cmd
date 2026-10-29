@echo off
title TradingQuant - Next.js local
cd /d "%~dp0..\apps\web"
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
echo.
echo TradingQuant Web: http://127.0.0.1:3000
echo No necesita token en modo local: API en 127.0.0.1.
call npm run dev -- --hostname 127.0.0.1
echo.
echo Next.js se cerro. Revisa el mensaje anterior.
pause
