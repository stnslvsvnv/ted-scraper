"""
TED Scraper Backend - Исправленная версия с учетом TED API v3
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Монтируем статические файлы (frontend)
app.mount("/static", StaticFiles(directory="."), name="static")

# Модели
class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None  # YYYY-MM-DD
    publication_date_to: Optional[str] = None    # YYYY-MM-DD
    country: Optional[str] = None
    # Можно добавить больше фильтров позже

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
    notices: List[Notice]  # Изменено для совместимости с фронтендом

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
SUPPORTED_FIELDS = ["publication-number", "publication-date", "title", "buyer", "country-of-buyer"]  # Базовые поддерживаемые поля

@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/search")
async def search_notices(request: SearchRequest):
    try:
        # Строим expert query из filters
        query_parts = []
        if request.filters:
            if request.filters.text:
                query_parts.append(f'({request.filters.text})')
            if request.filters.country:
                query_parts.append(f'country-of-buyer:{request.filters.country}')
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
            "page": request.page,
            "limit": request.limit,
            "scope": "LATEST",  # По умолчанию LATEST для актуальных
            "fields": SUPPORTED_FIELDS
        }
        
        logger.info(f"🔍 Searching TED API: query='{expert_query}', page={request.page}, limit={request.limit}")
        logger.info(f"Using {len(SUPPORTED_FIELDS)} fields")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=30.0)
        
        logger.info(f"📤 POST to {TED_API_URL}")
        logger.info(f"📥 Status: {response.status_code}")
        
        if response.status_code != 200:
            error_detail = response.json().get("detail", "Unknown error")
            logger.error(f"❌ API Error: {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=error_detail)
        
        data = response.json()
        total = data.get("total", 0)
        
        # Маппинг результатов к модели Notice (упрощенный)
        notices = []
        for item in data.get("results", []):
            notice = Notice(
                publication_number=item.get("publication-number", ""),
                publication_date=item.get("publication-date"),
                title=item.get("title"),
                buyer=item.get("buyer"),
                country=item.get("country-of-buyer")
            )
            notices.append(notice)
        
        return SearchResponse(total=total, notices=notices)
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
