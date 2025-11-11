FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование основных файлов
COPY app.py .
COPY index.html .

# Попытка копирования static, но если папки нет - игнорируем ошибку
RUN mkdir -p ./static
COPY static/ ./static/ 2>/dev/null || echo "Static files will be created at runtime"

# Expose порт
EXPOSE 8846

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8846/health || exit 1

# Запуск приложения
CMD ["python", "app.py"]
