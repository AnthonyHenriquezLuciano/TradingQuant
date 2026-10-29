FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/data/numba \
    TRADINGQUANT_DATA_DIR=/data/uploads
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8000
# Railway supplies PORT. A single worker keeps the in-memory job queue coherent.
# Attach one persistent Railway volume at /data (CSV + JIT cache).
CMD ["sh", "-c", "mkdir -p \"$TRADINGQUANT_DATA_DIR\" \"$NUMBA_CACHE_DIR\" && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
