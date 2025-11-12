FROM python:3.11-slim

WORKDIR /app

# Копируем все файлы из repo (app.py, index.html, style.css, script.js)
COPY . /app

# Установка зависимостей, включая python-multipart для Form
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic python-multipart

# Порт
EXPOSE 8846

# Запуск
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8846"]
