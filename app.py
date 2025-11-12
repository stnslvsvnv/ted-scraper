"""
TED Scraper Backend - Фикс 400: правильные fields для TED API v3
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging
import os

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

# API-роуты
TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
SUPPORTED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country"
]  # Валидные поля из TED API (без CONTENT)

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

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
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
        
        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "scope": "LATEST",
            "fields": SUPPORTED_FIELDS  # Теперь валидные поля
        }
        
        logger.info(f"🔍 TED API: query='{expert_query}', fields={SUPPORTED_FIELDS}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)
        
        logger.info(f"TED Response: {response.status_code}")
        
        if response.status_code != 200:
            try:
                error_detail = response.json()
                # Для 400: берём message для ясности
                if response.status_code == 400:
                    detail = error_detail.get("message", str(error_detail))
                else:
                    detail = error_detail.get("detail", response.text[:200])
            except:
                detail = response.text[:200]
            logger.error(f"TED Error ({response.status_code}): {detail}")
            raise HTTPException(status_code=response.status_code, detail=f"TED API error: {detail}")
        
        data = response.json()
        total = data.get("total", 0)
        
        notices = []
        for item in data.get("results", []):
            # Теперь поля напрямую в item (не в CONTENT)
            notice = Notice(
                publication_number=item.get("publication-number", ""),
                publication_date=item.get("publication-date"),
                title=item.get("notice-title"),
                buyer=item.get("buyer-name"),
                country=item.get("buyer-country")
            )
            notices.append(notice)
        
        logger.info(f"Returned {len(notices)} notices out of {total}")
        return SearchResponse(total=total, notices=notices)
    
    except httpx.RequestError as e:
        logger.error(f"TED Connection: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Static files на /static (CSS/JS)
app.mount("/static", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
