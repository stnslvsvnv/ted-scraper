# Multi-stage build для оптимизации размера
FROM python:3.11-slim as builder

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Устанавливаем curl для health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Копируем приложение
COPY app.py .
COPY index.html .
COPY static/ static/

# Expose порты
EXPOSE 8846 8847

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8846/health || exit 1

# Запуск
CMD ["python", "app.py"]
