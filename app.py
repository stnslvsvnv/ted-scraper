"""
TED Scraper Backend - Исправленная версия с фиксом ошибок
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse  # Добавлен импорт
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

# Модели
class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None  # YYYY-MM-DD
    publication_date_to: Optional[str] = None    # YYYY-MM-DD
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
SUPPORTED_FIELDS = ["CONTENT"]  # Используем агрегат CONTENT для базового ответа без ошибок

@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")

# Добавим endpoints для статических файлов (css, js)
@app.get("/style.css")
async def get_css():
    if not os.path.exists("style.css"):
        raise HTTPException(status_code=404, detail="style.css not found")
    return FileResponse("style.css")

@app.get("/script.js")
async def get_js():
    if not os.path.exists("script.js"):
        raise HTTPException(status_code=404, detail="script.js not found")
    return FileResponse("script.js")

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        # Строим expert query из filters
        query_parts = []
        if request.filters:
            if request.filters.text:
                query_parts.append(f'({request.filters.text})')
            if request.filters.country:
                query_parts.append(f'country-of-buyer:{request.filters.country.upper()}')
            if request.filters.publication_date_from:
                from_date = request.filters.publication_date_from.replace("-", "")  # YYYYMMDD
                query_parts.append(f'publication-date>={from_date}')
            if request.filters.publication_date_to:
                to_date = request.filters.publication_date_to.replace("-", "")  # YYYYMMDD
                query_parts.append(f'publication-date<={to_date}')
        
        expert_query = " AND ".join(query_parts) if query_parts else "*"
        
        logger.info(f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}")
        
        # Тело запроса к TED API
        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),  # Ограничения TED
            "scope": "LATEST",
            "fields": SUPPORTED_FIELDS
        }
        
        logger.info(f"🔍 Searching TED API: query='{expert_query}', page={request.page}, limit={request.limit}")
        logger.info(f"Using {len(SUPPORTED_FIELDS)} fields: {SUPPORTED_FIELDS}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=60.0)
        
        logger.info(f"📤 POST to {TED_API_URL}")
        logger.info(f"📥 Status: {response.status_code}")
        
        if response.status_code != 200:
            try:
                error_detail = response.json()
            except:
                error_detail = {"detail": response.text}
            logger.error(f"❌ API Error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"TED API error: {error_detail}")
        
        data = response.json()
        total = data.get("total", 0)
        
        # Маппинг результатов (адаптировано под реальные ключи TED API)
        notices = []
        for item in data.get("results", []):
            # CONTENT возвращает структурированный объект, извлекаем базовые поля
            content = item.get("CONTENT", {})
            notice = Notice(
                publication_number=content.get("publicationNumber", item.get("id", "")),
                publication_date=content.get("publicationDate"),
                title=content.get("title", content.get("shortTitle")),
                buyer=content.get("buyerName", content.get("buyer", {}).get("name")),
                country=content.get("country", content.get("buyer", {}).get("countryCode"))
            )
            notices.append(notice)
        
        logger.info(f"Found {len(notices)} notices")
        return SearchResponse(total=total, notices=notices)
    
    except httpx.RequestError as e:
        logger.error(f"TED API request error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8846)
