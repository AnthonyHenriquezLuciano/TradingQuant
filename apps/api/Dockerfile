FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/var/cache/numba TRADINGQUANT_DATA_DIR=/data/uploads
WORKDIR /app
RUN mkdir -p /data/uploads /var/cache/numba
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8000
# Exactly one process: jobs live in process memory. Distributed workers
# require an external queue and durable results database.
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--workers","1"]
