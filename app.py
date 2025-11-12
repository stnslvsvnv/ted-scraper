"""
TED Scraper Backend - Исправленная версия с StaticFiles и /health
"""

from fastapi import FastAPI, HTTPException, Form  # Добавлен Form для fallback
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # Для статических файлов
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tedapi")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы из текущей директории (index.html, style.css, script.js)
app.mount("/", StaticFiles(directory=".", html=True), name="static")  # html=True для index.html на /

# Модели (без изменений)
class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    country: Optional[str] = None

class SearchRequest(BaseModel):
    filters: Optional[Filters] = None
    page: int = 1
    limit: int = 25

class Notice(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    title: Optional[str] = None
    buyer: Optional[str] = None
    country: Optional[str] = None

class SearchResponse(BaseModel):
    total: int
    notices: List[Notice]

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
SUPPORTED_FIELDS = ["CONTENT"]  # Базовый агрегат для избежания ошибок

# Health endpoint для мониторинга
@app.get("/health")
async def health():
    return {"status": "ok", "service": "TED Scraper"}

# Основной root — теперь через StaticFiles, но для совместимости
@app.get("/")
async def read_root():
    return {"message": "TED Scraper API. Use / for frontend or /search for API."}

# JSON POST для JS (основной)
@app.post("/search")
async def search_notices_json(request: SearchRequest):
    return await search_notices_impl(request)

# Fallback для form-data (если JS не загрузился)
@app.post("/search")
async def search_notices_form(
    text: Optional[str] = Form(None),
    publication_date_from: Optional[str] = Form(None),
    publication_date_to: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    page: int = Form(1),
    limit: int = Form(25)
):
    filters_data = {}
    if text: filters_data['text'] = text
    if publication_date_from: filters_data['publication_date_from'] = publication_date_from
    if publication_date_to: filters_data['publication_date_to'] = publication_date_to
    if country: filters_data['country'] = country
    request = SearchRequest(filters=Filters(**filters_data) if filters_data else None, page=page, limit=limit)
    return await search_notices_impl(request)

# Общая реализация поиска
async def search_notices_impl(request: SearchRequest):
    try:
        # Строим expert query
        query_parts = []
        if request.filters:
            if request.filters.text:
                query_parts.append(f'({request.filters.text})')
            if request.filters.country:
                query_parts.append(f'country-of-buyer:{request.filters.country.upper()}')
            if request.filters.publication_date_from:
                from_date = request.filters.publication_date_from.replace("-", "")
                query_parts.append(f'publication-date>={from_date}')
            if request.filters.publication_date_to:
                to_date = request.filters.publication_date_to.replace("-", "")
                query_parts.append(f'publication-date<={to_date}')
        
        expert_query = " AND ".join(query_parts) if query_parts else "*"
        
        logger.info(f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}")
        
        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "scope": "LATEST",
            "fields": SUPPORTED_FIELDS
        }
        
        logger.info(f"🔍 TED API: query='{expert_query}', fields={SUPPORTED_FIELDS}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)  # Увеличен timeout
        
        logger.info(f"TED Response: {response.status_code}")
        
        if response.status_code != 200:
            try:
                error_detail = response.json()
            except:
                error_detail = {"detail": response.text[:200]}
            logger.error(f"TED Error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"TED API: {error_detail}")
        
        data = response.json()
        total = data.get("total", 0)
        
        # Маппинг (упрощённый для CONTENT)
        notices = []
        for item in data.get("results", []):
            content = item.get("CONTENT", {})
            notice = Notice(
                publication_number=content.get("publicationNumber", str(item.get("id", ""))),
                publication_date=content.get("publicationDate"),
                title=content.get("title") or content.get("shortTitle", "No title"),
                buyer=content.get("buyerName") or content.get("buyer", {}).get("name", "Unknown buyer"),
                country=content.get("country") or content.get("buyer", {}).get("countryCode", "Unknown")
            )
            notices.append(notice)
        
        logger.info(f"Returned {len(notices)} notices out of {total}")
        return SearchResponse(total=total, notices=notices)
    
    except httpx.RequestError as e:
        logger.error(f"TED Connection: {e}")
        raise HTTPException(status_code=502, detail=f"Connection: {str(e)}")
    except Exception as e:
        logger.error(f"Search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8846"))
    uvicorn.run(app, host="0.0.0.0", port=port)
