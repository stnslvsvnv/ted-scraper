FROM python:3.11-slim

WORKDIR /app

# Копируем все файлы из repo (build context)
COPY . /app

# Установка зависимостей
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

# Порт по умолчанию
EXPOSE 8846

# Запуск
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8846"]