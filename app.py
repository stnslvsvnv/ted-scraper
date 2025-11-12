"""
TED Scraper Backend - Fixed version with correct response parsing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

SUPPORTED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country"
]

API_KEY = os.getenv("TED_API_KEY", None)

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
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}

@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")

def get_historical_broad():
    return "(publication-date >= 19930101)"

def extract_multilang_field(field_value: Any, default: str = "N/A") -> str:
    """
    Извлекает значение из многоязычного поля.
    API может возвращать строку или словарь типа {"eng": ["value1"], "fra": ["value2"]}
    """
    if isinstance(field_value, str):
        return field_value
    elif isinstance(field_value, dict):
        # Берем первый доступный язык
        for lang_values in field_value.values():
            if isinstance(lang_values, list) and lang_values:
                return lang_values[0]
            elif isinstance(lang_values, str):
                return lang_values
    elif isinstance(field_value, list) and field_value:
        return field_value[0] if isinstance(field_value[0], str) else str(field_value[0])
    return default

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        query_terms = []
        
        if request.filters:
            if request.filters.text:
                text = request.filters.text.strip()
                ft_term = f'(notice-title ~ "{text}" OR buyer-name ~ "{text}")'
                query_terms.append(ft_term)
            
            if request.filters.country:
                query_terms.append(f'(buyer-country = {request.filters.country.upper()})')
            
            if request.filters.publication_date_from:
                from_date = request.filters.publication_date_from.replace("-", "")
                if from_date:
                    query_terms.append(f'(publication-date >= {from_date})')
            
            if request.filters.publication_date_to:
                to_date = request.filters.publication_date_to.replace("-", "")
                if to_date:
                    query_terms.append(f'(publication-date <= {to_date})')
        
        if not query_terms:
            expert_query = get_historical_broad()
        else:
            expert_query = " AND ".join(query_terms)
        
        logger.info(f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}")
        
        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "fields": SUPPORTED_FIELDS
        }
        
        if API_KEY:
            payload["apiKey"] = API_KEY
        
        logger.info(f"Payload: {payload}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.json().get("message", response.text[:200]) if response.content else "No response"
                logger.error(f"TED Error ({response.status_code}): {error_detail}")
                raise HTTPException(status_code=response.status_code, detail=f"TED API error: {error_detail}")
            
            data = response.json()
            
            # ИСПРАВЛЕНО: API возвращает 'notices', а не 'results'
            notices_data = data.get("notices", [])
            
            # ИСПРАВЛЕНО: total может отсутствовать, считаем через len()
            total = data.get("total", len(notices_data))
            
            logger.info(f"Total results: {total} notices")
            logger.info(f"Received {len(notices_data)} notices in response")
            
            notices = []
            for item in notices_data:
                # ИСПРАВЛЕНО: обработка многоязычных полей
                notice = Notice(
                    publication_number=item.get("publication-number", "N/A"),
                    publication_date=item.get("publication-date"),
                    title=extract_multilang_field(item.get("notice-title"), "No title"),
                    buyer=extract_multilang_field(item.get("buyer-name"), "Unknown buyer"),
                    country=extract_multilang_field(item.get("buyer-country"), "Unknown")
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

app.mount("/static", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
