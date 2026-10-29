# Gestión del proyecto TradingQuant

## Responsabilidad de implementación

El usuario define requisitos, funcionalidades, preferencias visuales y prioridades. El asistente de desarrollo es responsable de implementar integralmente los cambios en el repositorio, modificar frontend y backend, actualizar tests, verificar los pipelines y comprobar los despliegues de Vercel sin trasladar al usuario tareas técnicas rutinarias.

Para cada solicitud:
1. Inspeccionar el estado real del repositorio y conservar las funcionalidades existentes.
2. Implementar directamente los cambios solicitados en el código.
3. Integrar parámetros visuales al motor cuando se declare que afectan el backtesting.
4. Escribir y ejecutar pruebas relevantes; corregir errores antes de declarar el trabajo completado.
5. Verificar GitHub Actions y el último despliegue de Vercel, comunicando claramente las limitaciones.
6. Solicitar intervención del usuario únicamente cuando de verdad sea necesaria una autorización externa, una cuenta conectada o un dato imprescindible.

No confundir opciones visuales guardadas con funcionalidades científicas operativas ni presentar simulaciones OHLC como datos tick reales.

## Plataforma actual

Frontend Next.js / React, diseño negro con dorado sutil. Backend Python FastAPI + Polars + Numba. Sesiones persistidas localmente en navegador. Vercel hospeda el frontend; el backend de investigación aún requiere despliegue público e integración operativa. Las tareas de despliegue no se deben dar por terminadas hasta comprobar el estado READY y los tests.
