# TED Scraper - Setup & Deployment Guide

## 📦 Installation

### Prerequisites

- Docker & Docker Compose, OR
- Python 3.11+
- 50MB disk space
- Internet connection (for TED API calls)

### Step 1: Get the Code

```bash
# Option A: Git clone
git clone https://github.com/yourusername/ted-scraper.git
cd ted-scraper

# Option B: Download and extract zip
unzip ted-scraper-main.zip
cd ted-scraper-main
```

### Step 2: Verify Structure

```bash
ls -la

# Expected files:
# app.py
# index.html
# static/
#   ├── style.css
#   └── script.js
# requirements.txt
# Dockerfile
# docker-compose.yml
# README.md
# SETUP.md
```

---

## 🐳 Docker Setup (Recommended)

### Build & Run

```bash
# Build the image
docker-compose build

# Run the container
docker-compose up -d

# Check if running
docker-compose ps

# View logs
docker-compose logs -f ted-scraper

# Access
# Frontend: http://localhost:8846
# API: http://localhost:8846/api/docs
```

### Debugging

```bash
# See logs
docker-compose logs ted-scraper

# Enter container
docker-compose exec ted-scraper bash

# Restart service
docker-compose restart ted-scraper

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up

# Stop and remove
docker-compose down
```

### Custom Port

Edit `docker-compose.yml`:

```yaml
services:
  ted-scraper:
    ports:
      - "9000:8846"  # Access on http://localhost:9000
```

Then:

```bash
docker-compose up --build
```

---

## 🐍 Local Python Setup

### Windows

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python app.py

# Access: http://localhost:8846
```

### macOS/Linux

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python app.py

# Access: http://localhost:8846
```

### Troubleshooting

```bash
# Port already in use?
# Kill process on port 8846
lsof -ti :8846 | xargs kill -9  # macOS/Linux
netstat -ano | findstr 8846     # Windows (then taskkill)

# Python not found?
# Check version
python --version   # or python3 --version

# Dependencies error?
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

## 🚀 Deployment

### Cloud Platforms

#### Heroku

```bash
# 1. Create app
heroku create ted-scraper

# 2. Create Procfile (if not exists)
echo "web: python app.py" > Procfile

# 3. Deploy
git push heroku main

# 4. View logs
heroku logs -t

# 5. Open app
heroku open
```

#### AWS (Docker)

```bash
# 1. Build image
docker build -t ted-scraper:latest .

# 2. Tag for ECR
aws ecr get-login-password --region us-east-1 | docker login \
  --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker tag ted-scraper:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ted-scraper:latest

# 3. Push to ECR
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/ted-scraper:latest

# 4. Create task definition and service in ECS
# (Use AWS Console or CLI)
```

#### Google Cloud Run

```bash
# 1. Configure gcloud
gcloud auth login
gcloud config set project PROJECT_ID

# 2. Build and push
gcloud run deploy ted-scraper \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### DigitalOcean

```bash
# 1. Create droplet with Docker
# 2. SSH into droplet
ssh root@<DROPLET_IP>

# 3. Clone repository
git clone https://github.com/yourusername/ted-scraper.git
cd ted-scraper

# 4. Run with docker-compose
docker-compose up -d

# 5. Configure reverse proxy (nginx)
# Point domain to http://localhost:8846
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file (optional):

```bash
# Log level: debug, info, warning, error
LOG_LEVEL=info

# TED API timeout (seconds)
TED_API_TIMEOUT=30

# Frontend port
FRONTEND_PORT=8846
```

Or set in `docker-compose.yml`:

```yaml
environment:
  - LOG_LEVEL=info
  - TED_API_TIMEOUT=30
```

### Port Configuration

#### Docker

Edit `docker-compose.yml`:

```yaml
ports:
  - "EXTERNAL_PORT:8846"
```

#### Python

In `app.py`:

```python
uvicorn.run(
    "app:app",
    host="0.0.0.0",
    port=9000,  # Change port here
    ...
)
```

#### Frontend API URL

Edit `static/script.js`:

```javascript
const CONFIG = {
    BACKEND_BASE_URL: 'http://localhost:8846',  // Change URL here
    REQUEST_TIMEOUT: 30000
};
```

---

## 📊 Monitoring

### Health Checks

```bash
# Check service health
curl http://localhost:8846/health

# Response:
# {
#   "status": "healthy",
#   "ted_api_available": true,
#   "timestamp": "2025-01-15T14:30:00"
# }
```

### Logs

#### Docker

```bash
# View logs
docker-compose logs ted-scraper

# Follow logs
docker-compose logs -f ted-scraper

# Last 100 lines
docker-compose logs --tail=100 ted-scraper

# Since specific time
docker-compose logs --since 2025-01-15T10:00:00 ted-scraper
```

#### Python (Local)

Logs appear in console where you run `python app.py`

### Performance Metrics

Access API stats:

```bash
curl http://localhost:8846/statistics

# Response:
# {
#   "total_tasks": 10,
#   "completed": 8,
#   "failed": 1,
#   "pending": 1,
#   "success_rate": 80
# }
```

---

## 🔒 Security

### Basic Firewall Rules

```bash
# Allow only port 8846
sudo ufw allow 8846/tcp

# Block other ports
sudo ufw enable
```

### HTTPS/SSL

Option 1: Use reverse proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8846;
    }
}
```

Option 2: Use Caddy (automatic HTTPS)

```bash
# Install Caddy
# Then create Caddyfile:
example.com {
    reverse_proxy localhost:8846
}

# Run
caddy run
```

### Rate Limiting

Add to `app.py` (requires `slowapi`):

```bash
pip install slowapi
```

Then in app.py:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/search")
@limiter.limit("10/minute")
async def search(request: SearchRequest):
    ...
```

---

## 🧪 Testing

### Unit Tests

```bash
# Create test file: tests/test_api.py
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### Load Testing

```bash
# Install Apache Bench
# macOS: brew install httpd
# Ubuntu: sudo apt-get install apache2-utils

# Test 100 requests with 10 concurrent
ab -n 100 -c 10 http://localhost:8846/health
```

### Integration Tests

```bash
# Using curl
#!/bin/bash

# Test health
curl -f http://localhost:8846/health || exit 1

# Test search
curl -f -X POST http://localhost:8846/search \
  -H "Content-Type: application/json" \
  -d '{"filters":{},"page":1,"page_size":10}' || exit 1

echo "✓ All tests passed"
```

---

## 📋 Maintenance

### Updates

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Rebuild Docker image
docker-compose build --no-cache
docker-compose up -d
```

### Backups

The application doesn't store data locally, so no backups needed. All data comes from TED API.

### Clean Up

```bash
# Remove old images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a
```

---

## 🆘 Common Issues

### "Connection refused"

```
Error: Failed to connect to http://localhost:8846

Solution:
1. Check if service is running: docker-compose ps
2. Check logs: docker-compose logs ted-scraper
3. Verify port: netstat -an | grep 8846
```

### "TED API Timeout"

```
Error: TED API timeout or connection error

Solution:
1. Check internet connection: ping ted.europa.eu
2. Wait a moment (TED API can be slow)
3. Try different search filters (reduce result size)
4. Increase timeout in app.py: REQUEST_TIMEOUT = 60
```

### "Port already in use"

```
Error: Address already in use

Solution:
docker-compose down  # Stop all services
docker-compose up    # Start again

Or use different port in docker-compose.yml
```

### "Out of memory"

```
Solution:
# Limit Docker memory
docker-compose down
# Edit docker-compose.yml and add:
# mem_limit: 512m
docker-compose up
```

---

## 📚 Additional Resources

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Docker Docs](https://docs.docker.com)
- [TED API Docs](https://ted.europa.eu/api/documentation/index.html)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)

---

**Deployment Complete! 🎉**
