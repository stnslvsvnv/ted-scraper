# Оптимизированный Dockerfile для Portainer

FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY app.py .
COPY index.html .
COPY static/ static/

# Expose порт
EXPOSE 8846

# Health check с коротким путём
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8846/health || exit 1

# Запуск приложения
CMD ["python", "app.py"]
