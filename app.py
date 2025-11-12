"""
TED Scraper Backend - Финал: historical broad date fallback "(publication-date >= 19930101)", mandatory valid query
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

def get_historical_broad():
    """Broad date from TED start for match all"""
    return "(publication-date >= 19930101)"

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        query_terms = []
        has_date_filter = False
        if request.filters:
            if request.filters.text:
                text = request.filters.text.strip()
                # Field-specific fuzzy for reliable matches
                ft_term = f'(notice-title ~ {text} OR buyer-name ~ {text})'
                query_terms.append(ft_term)
            
            if request.filters.country:
                query_terms.append(f'(country-of-buyer = {request.filters.country.upper()})')
            
            if request.filters.publication_date_from:
                from_date = request.filters.publication_date_from.replace("-", "")
                if from_date:
                    query_terms.append(f'(publication-date >= {from_date})')
                    has_date_filter = True
            
            if request.filters.publication_date_to:
                to_date = request.filters.publication_date_to.replace("-", "")
                if to_date:
                    query_terms.append(f'(publication-date <= {to_date})')
                    has_date_filter = True
        
        # If no terms or only empty dates, use historical broad for all
        if not query_terms or (has_date_filter and not request.filters.text and not request.filters.country):
            expert_query = get_historical_broad()
            if request.filters.text:
                query_terms = [f'(notice-title ~ {request.filters.text.strip()} OR buyer-name ~ {request.filters.text.strip()})']
            elif request.filters.country:
                query_terms = [f'(country-of-buyer = {request.filters.country.upper()})']
            else:
                query_terms = []
            if query_terms:
                expert_query = f"{expert_query} AND " + " AND ".join(query_terms)
        else:
            expert_query = " AND ".join(query_terms)
        
        logger.info(f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}")
        
        payload = {
            "query": expert_query,  # Always valid non-empty
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "scope": "LATEST",
            "fields": SUPPORTED_FIELDS
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)
            data = response.json()
            total = data.get("total", 0)
            logger.info(f"Initial total: {total} lots")
            
            # Fallback to ALL if 0
            if total == 0:
                logger.info("Initial 0; retry ALL")
                payload["scope"] = "ALL"
                response = await client.post(TED_API_URL, json=payload, timeout=120.0)
                data = response.json()
                total = data.get("total", 0)
                logger.info(f"ALL total: {total} lots")
            
            # Final fallback: historical broad + terms if any
            if total == 0:
                logger.info("Still 0; historical broad fallback")
                historical = get_historical_broad()
                if request.filters and (request.filters.text or request.filters.country):
                    terms = []
                    if request.filters.text:
                        terms.append(f'(notice-title ~ {request.filters.text.strip()} OR buyer-name ~ {request.filters.text.strip()})')
                    if request.filters.country:
                        terms.append(f'(country-of-buyer = {request.filters.country.upper()})')
                    expert_query = f"{historical} AND " + " AND ".join(terms)
                else:
                    expert_query = historical
                payload["query"] = expert_query
                payload["scope"] = "ALL"
                response = await client.post(TED_API_URL, json=payload, timeout=120.0)
                data = response.json()
                total = data.get("total", 0)
                logger.info(f"Historical fallback total: {total} lots")
        
        if response.status_code != 200:
            error_detail = response.json().get("message", response.text[:200]) if response.content else "No response"
            logger.error(f"TED Error ({response.status_code}): {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=f"TED API error: {error_detail}")
        
        notices = []
        for item in data.get("results", []):
            notice = Notice(
                publication_number=item.get("publication-number", "N/A"),
                publication_date=item.get("publication-date"),
                title=item.get("notice-title", "No title"),
                buyer=item.get("buyer-name", "Unknown buyer"),
                country=item.get("buyer-country", "Unknown")
            )
            notices.append(notice)
        
        logger.info(f"Returned {len(notices)} lots out of {total}")
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
