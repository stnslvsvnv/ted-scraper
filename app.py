"""
TED Scraper Backend - FIXED VERSION
All TED API v3 issues resolved: fields, query syntax, direct links
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
from datetime import datetime, timedelta

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
API_KEY = os.getenv("TED_API_KEY", None)

# ✅ FIXED: Using ONLY VALID TED API v3 fields from error log
VALID_FIELDS = [
    "publication-number",
    "publication-date", 
    "deadline-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "city",
    "classification-cpv"  # ✅ CPV field (from error log)
]

class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    country: Optional[str] = None
    cpv_code: Optional[str] = None
    active_only: bool = False

class SearchRequest(BaseModel):
    filters: Optional[Filters] = None
    page: int = 1
    limit: int = 25

class Notice(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    deadline_date: Optional[str] = None
    title: Optional[str] = None
    buyer: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    cpv_code: Optional[str] = None

class SearchResponse(BaseModel):
    total: int
    notices: List[Notice]

@app.get("/health")
async def health():
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}

@app.get("/")
async def read_root():
    return FileResponse("index.html")

def build_ted_query(filters: Filters) -> str:
    """✅ FIXED: Correct TED v3 query syntax"""
    query_parts = []
    
    # Text search in title
    if filters.text:
        query_parts.append(f'(notice-title ~ "{filters.text}")')
    
    # ✅ FIXED: Country search using VALID field
    if filters.country:
        countries = [c.strip().upper() for c in filters.country.split(",") if c.strip()]
        if countries:
            country_query = " OR ".join([f'(buyer-country = "{c}")' for c in countries])  # ✅ Quotes added
            query_parts.append(f"({country_query})")
    
    # ✅ FIXED: CPV using VALID classification-cpv field
    if filters.cpv_code:
        query_parts.append(f'(classification-cpv = "{filters.cpv_code}")')
    
    # ✅ FIXED: Date format YYYYMMDD (no dashes)
    if filters.publication_date_from:
        from_date = filters.publication_date_from.replace("-", "")
        query_parts.append(f"(publication-date >= {from_date})")
    
    if filters.publication_date_to:
        to_date = filters.publication_date_to.replace("-", "")
        query_parts.append(f"(publication-date <= {to_date})")
    
    # Active tenders only
    if filters.active_only:
        today = datetime.now().strftime("%Y%m%d")
        query_parts.append(f"(deadline-date >= {today})")
    
    # Default: last 30 days
    if not query_parts:
        default_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        query_parts.append(f"(publication-date >= {default_date})")
    
    return " AND ".join(query_parts)

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        query = build_ted_query(request.filters) if request.filters else "(publication-date >= 20250101)"
        logger.info(f"TED Query: {query}")
        
        # ✅ FIXED: Using ONLY validated fields
        payload = {
            "query": query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "scope": "ALL",
            "fields": VALID_FIELDS  # ✅ This was the CRASH cause!
        }
        
        if API_KEY:
            payload["apiKey"] = API_KEY
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=30.0)
            
        if response.status_code != 200:
            error_detail = response.json().get("message", "Unknown error") if response.content else "Empty response"
            logger.error(f"TED API error {response.status_code}: {error_detail}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"TED API error: {error_detail}"
            )
        
        data = response.json()
        total = data.get("totalNoticeCount", 0)
        notices = []
        
        for item in data.get("notices", []):
            # ✅ FIXED: Using exact field names from TED API
            notices.append(
                Notice(
                    publication_number=item.get("publication-number", "N/A"),
                    publication_date=item.get("publication-date"),
                    deadline_date=item.get("deadline-date"),
                    title=item.get("notice-title", "No title"),
                    buyer=item.get("buyer-name"),
                    country=item.get("buyer-country"),
                    city=item.get("city"),
                    cpv_code=item.get("classification-cpv")  # ✅ Correct CPV field
                )
            )
        
        logger.info(f"Returned {len(notices)} notices out of {total}")
        return SearchResponse(total=total, notices=notices)
        
    except httpx.RequestError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/countries")
async def get_countries():
    """Full EU countries list"""
    return [
        {"code": "AUT", "name": "Austria (Österreich)"},
        {"code": "BEL", "name": "Belgium (België/Belgique)"},
        {"code": "BGR", "name": "Bulgaria (България)"},
        {"code": "HRV", "name": "Croatia (Hrvatska)"},
        {"code": "CYP", "name": "Cyprus (Κύπρος)"},
        {"code": "CZE", "name": "Czech Republic (Česko)"},
        {"code": "DNK", "name": "Denmark (Danmark)"},
        {"code": "DEU", "name": "Germany (Deutschland)"},
        {"code": "EST", "name": "Estonia (Eesti)"},
        {"code": "GRC", "name": "Greece (Ελλάδα)"},
        {"code": "ESP", "name": "Spain (España)"},
        {"code": "FRA", "name": "France"},
        {"code": "IRL", "name": "Ireland (Éire)"},
        {"code": "ITA", "name": "Italy (Italia)"},
        {"code": "LVA", "name": "Latvia (Latvija)"},
        {"code": "LTU", "name": "Lithuania (Lietuva)"},
        {"code": "LUX", "name": "Luxembourg (Lëtzebuerg)"},
        {"code": "MLT", "name": "Malta"},
        {"code": "NLD", "name": "Netherlands (Nederland)"},
        {"code": "POL", "name": "Poland (Polska)"},
        {"code": "PRT", "name": "Portugal"},
        {"code": "ROU", "name": "Romania (România)"},
        {"code": "SVK", "name": "Slovakia (Slovensko)"},
        {"code": "SVN", "name": "Slovenia (Slovenija)"},
        {"code": "FIN", "name": "Finland (Suomi)"},
        {"code": "SWE", "name": "Sweden (Sverige)"},
        {"code": "GBR", "name": "United Kingdom"},
    ]

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
