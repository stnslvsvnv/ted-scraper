# TED Scraper - Complete Documentation

## 📋 Overview

**TED Scraper** is a full-stack web application for searching European public procurement notices (tenders) from the **Tenders Electronic Daily (TED)** system.

### Features

✅ **Advanced Search Interface** — Like TED's official Advanced Search  
✅ **Real-time Results** — Live data from TED API v3.0  
✅ **Responsive Design** — Works on desktop, tablet, and mobile  
✅ **Microservice Architecture** — Ready for extensions (PDF extraction, archiving, etc.)  
✅ **Docker Ready** — Single container for deployment  
✅ **No Authentication** — Use public TED API freely  

### Architecture

```
┌─────────────────────────────────────────────┐
│      Frontend (Port 8846)                   │
│  ├─ Advanced Search Form (HTML/CSS/JS)     │
│  ├─ Results Table with Pagination          │
│  └─ Notice Details Modal                   │
├─────────────────────────────────────────────┤
│      Backend API (Port 8846)                │
│  ├─ /search → Find tenders                 │
│  ├─ /notice/{id} → Get details             │
│  ├─ /process → Microservice tasks          │
│  └─ /health → Status check                 │
├─────────────────────────────────────────────┤
│      TED API v3.0 (External)                │
│  └─ https://ted.europa.eu/api/...          │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Clone or download the project
cd ted-scraper

# Build and run
docker-compose up --build

# Access
# Frontend: http://localhost:8846
# API Docs: http://localhost:8846/api/docs

# Stop
docker-compose down
```

### Option 2: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python app.py

# Access
# Frontend: http://localhost:8846
# API Docs: http://localhost:8846/api/docs
```

---

## 📁 Project Structure

```
ted-scraper/
├── app.py                 # Main FastAPI application (Frontend + Backend)
├── index.html            # Frontend HTML
├── static/
│   ├── style.css        # Frontend styles
│   └── script.js        # Frontend JavaScript
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose
├── README.md            # This file
├── SETUP.md             # Setup instructions
└── API.md               # API documentation
```

---

## 🔧 Configuration

### Ports

- **8846** — Frontend + Backend (combined)
- **8847** — Backend API (alternative, if running separately)

### Environment Variables

```bash
# Optional (set in docker-compose.yml or environment)
LOG_LEVEL=info          # Logging level: debug, info, warning, error
TED_API_TIMEOUT=30      # Timeout for TED API calls (seconds)
```

---

## 💻 Using the Frontend

### Advanced Search Form

**Left Panel** contains the search form with sections:

1. **Text** — Full-text search keywords
2. **Subject Matter** — CPV codes (Common Procurement Vocabulary)
3. **Buyer Information** — Countries (ISO 3-letter codes)
4. **Publication Period** — Date range
5. **Contract Value** — Min/max budget
6. **Search Options** — Scope, sorting, results per page

### Results Table

**Right Panel** shows:

- Expandable/collapsible results table
- Columns: Pub. Number, Date, Title, Buyer, Country, CPV, Est. Value, Action
- Click any row to view full notice details
- Pagination for browsing pages

### Workflow

1. **Fill Search Form** — Use any or all filters
2. **Click Search** — Send to backend
3. **View Results** — See matching tenders
4. **Click Row** — View full details in modal
5. **Edit Search** — Modify and search again

---

## 🔌 API Endpoints

### Public Endpoints (No Auth Required)

#### **POST** `/search`
Search for tenders

**Request:**
```json
{
  "filters": {
    "full_text": "engineering",
    "cpv_codes": ["71000000"],
    "buyer_countries": ["DEU", "FRA"],
    "publication_date_from": "2025-01-01",
    "publication_date_to": "2025-12-31",
    "min_value": 100000,
    "max_value": 5000000
  },
  "page": 1,
  "page_size": 25,
  "scope": "ACTIVE",
  "sort_column": "publication-number",
  "sort_order": "DESC"
}
```

**Response:**
```json
{
  "total_notices": 1250,
  "total_pages": 50,
  "current_page": 1,
  "page_size": 25,
  "notices": [
    {
      "publication_number": "2025/S1-123456789",
      "publication_date": "2025-01-15",
      "title": "Engineering Services",
      "buyer_name": "City of Munich",
      "country": "DE",
      "cpv_codes": ["71000000"],
      "estimated_value": 500000,
      "url": "https://ted.europa.eu/en/notice/2025/S1-123456789"
    }
  ],
  "search_query": "FT=engineering AND classification-cpv = 71000000 AND ...",
  "timestamp": "2025-01-15T14:30:00"
}
```

#### **GET** `/notice/{notice_id}`
Get full notice details

**Example:**
```
GET /notice/2025/S1-123456789
```

**Response:**
```json
{
  "publication_number": "2025/S1-123456789",
  "publication_date": "2025-01-15",
  "title": "Engineering Services",
  "buyer_name": "City of Munich",
  "country": "DE",
  "cpv_codes": ["71000000"],
  "estimated_value": 500000,
  "content_html": "<html>... full notice content ...",
  "url": "https://ted.europa.eu/en/notice/2025/S1-123456789",
  "metadata": { }
}
```

#### **GET** `/health`
Check server health

**Response:**
```json
{
  "status": "healthy",
  "ted_api_available": true,
  "timestamp": "2025-01-15T14:30:00"
}
```

#### **POST** `/process`
Create a microservice task (e.g., PDF extraction)

**Request:**
```json
{
  "task_id": "task-pdf-001",
  "task_type": "pdf_extract",
  "notice_ids": ["2025/S1-123456789"],
  "parameters": {
    "extract_format": "text",
    "language": "en"
  }
}
```

**Response:** `202 Accepted`
```json
{
  "task_id": "task-pdf-001",
  "status": "accepted",
  "message": "Task accepted"
}
```

#### **GET** `/process/{task_id}`
Get task status

**Response:**
```json
{
  "task_id": "task-pdf-001",
  "status": "pending",
  "created_at": "2025-01-15T14:30:00",
  "task_type": "pdf_extract"
}
```

#### **GET** `/statistics`
Get processing statistics

**Response:**
```json
{
  "total_tasks": 10,
  "completed": 8,
  "failed": 1,
  "pending": 1,
  "success_rate": 80
}
```

---

## 🔍 Search Filter Reference

### Text
- Full-text keyword search across all notice fields

### Subject Matter
- **CPV Codes** — Comma-separated, e.g.: `71000000, 72000000`
  - [View CPV list](https://simap.ted.europa.eu/web/simap/cpv)

### Buyer Information
- **Countries** — ISO 3-letter codes, e.g.: `DEU, FRA, ITA`
  - Common codes: DEU (Germany), FRA (France), ITA (Italy), ESP (Spain), BEL (Belgium)

### Publication Period
- Date range for notice publication

### Contract Value
- Minimum and maximum estimated contract value in EUR

### Search Options
- **Scope** — Active, Archived, All notices
- **Sort By** — Publication Number, Date, Notice Type, Buyer Name
- **Order** — Ascending or Descending
- **Results per Page** — 10, 25, 50, 100

---

## 🛠️ Troubleshooting

### "Backend: Offline" in Frontend

**Cause:** Backend API not accessible  
**Solution:**
```bash
# Check if service is running
docker-compose logs ted-scraper

# Verify port is available
netstat -an | grep 8846  # Linux/Mac
netstat -ano | findstr 8846  # Windows

# Restart service
docker-compose restart ted-scraper
```

### "Search failed" error

**Cause:** TED API unreachable  
**Solution:**
```bash
# Check internet connection
ping ted.europa.eu

# Check TED API status
curl https://ted.europa.eu/api/v3.0/notices/search

# Check backend logs
docker-compose logs -f ted-scraper
```

### "Port already in use"

**Cause:** Port 8846 is already occupied  
**Solution:**
```bash
# Option 1: Stop the service using that port
# Option 2: Change port in docker-compose.yml
# ports:
#   - "8850:8846"  # Use 8850 instead

docker-compose down
docker-compose up --build
```

### Slow search results

**Cause:** TED API response time or large result set  
**Solution:**
- Add more filters to narrow results
- Reduce date range
- Wait for TED API response (can take 10-30 seconds for large queries)

---

## 📊 Performance

- **Search Response Time** — 5-30 seconds (depends on query complexity)
- **Max Results Per Query** — 15,000 (TED API limitation)
- **Results Per Page** — 10-100
- **API Timeout** — 30 seconds

---

## 🔐 Security

- **No Authentication Required** — Uses public TED API
- **No Sensitive Data** — Only searches public tender information
- **CORS Enabled** — Frontend can call API from any domain (configurable)

---

## 🚢 Deployment

### Docker Hub

```bash
# Build and push to Docker Hub
docker build -t your-username/ted-scraper .
docker push your-username/ted-scraper

# Run from Docker Hub
docker run -p 8846:8846 your-username/ted-scraper
```

### Cloud Platforms

**Heroku:**
```bash
git push heroku main
```

**AWS ECS:**
- Create ECR repository
- Push image
- Create task definition
- Launch service

**Google Cloud Run:**
```bash
gcloud run deploy ted-scraper --image ted-scraper:latest
```

**Azure Container Instances:**
```bash
az container create --image ted-scraper:latest --ports 8846
```

---

## 🧪 Testing

### Frontend Testing

Open browser: `http://localhost:8846`

1. Try empty search → Should return all active notices
2. Search with CPV → Should filter by commodity codes
3. Search with country → Should filter by buyer country
4. Pagination → Should navigate pages

### API Testing

Using cURL:

```bash
# Health check
curl http://localhost:8846/health

# Simple search
curl -X POST http://localhost:8846/search \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {"full_text": "engineering"},
    "page": 1,
    "page_size": 10
  }'

# Get notice details
curl http://localhost:8846/notice/2025/S1-123456789
```

Using Python:

```python
import requests

# Search
response = requests.post(
    'http://localhost:8846/search',
    json={
        'filters': {'full_text': 'engineering'},
        'page': 1,
        'page_size': 10
    }
)
print(response.json())
```

---

## 📚 Additional Resources

- [TED Official Site](https://ted.europa.eu)
- [TED Advanced Search](https://ted.europa.eu/en/advanced-search)
- [TED API Documentation](https://ted.europa.eu/api/documentation/index.html)
- [CPV Codes](https://simap.ted.europa.eu/web/simap/cpv)
- [EU Country Codes](https://publications.europa.eu/en/web/about-us/databases/atu)

---

## 🤝 Contributing

To extend the application:

1. **Add new filters** — Modify `SearchFilters` model in `app.py`
2. **Add microservices** — Use `/process` endpoint
3. **Customize UI** — Edit `index.html`, `static/style.css`, `static/script.js`
4. **Change ports** — Update `docker-compose.yml` and `CONFIG` in `script.js`

---

## 📝 License

TED Scraper, 2025

---

## 🆘 Support

**Issues:**
- Check troubleshooting section above
- Review backend logs: `docker-compose logs ted-scraper`
- Check browser console: Right-click → Inspect → Console tab

**Questions:**
- Refer to [TED Help](https://ted.europa.eu/en/help)
- Review API docs: http://localhost:8846/api/docs

---

**Ready to start? Run `docker-compose up --build` and open http://localhost:8846** 🎉
