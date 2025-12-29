"""
TED Scraper Backend – БЕЗ Pydantic проблем с мультиязычными данными
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Any, Dict, Union
import httpx
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tedapi")

app = FastAPI(title="TED Scraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
API_KEY = os.getenv("TED_API_KEY")

SEARCH_FIELDS = [
    "publication-number",
    "publication-date", 
    "notice-title",
    "buyer-name",
    "buyer-country",
    "deadline-date-part",
    "organisation-city-buyer"
]

def safe_extract(value: Any) -> str:
    """Агрессивная обработка TED данных → строка"""
    if value is None:
        return ""
    
    # Если уже строка
    if isinstance(value, str):
        return value[:200]
    
    # Если число
    if isinstance(value, (int, float)):
        return str(value)
    
    # Рекурсивно разбираем
    def dig_deep(v):
        if isinstance(v, str):
            return v[:200]
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list) and len(v) > 0:
            return dig_deep(v[0])
        if isinstance(v, dict):
            # Первый язык из мультиязычного
            first_val = next(iter(v.values()), None)
            if first_val:
                return dig_deep(first_val)
        return str(v)[:200]
    
    return dig_deep(value)

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

# ПРОСТАЯ модель БЕЗ Optional[str] проблем
class SimpleNotice(BaseModel):
    publication_number: str
    publication_date: str = ""
    deadline_date: str = ""
    title: str = ""
    buyer: str = ""
    country: str = ""
    city: str = ""
    cpv_code: str = ""

class SearchResponse(BaseModel):
    total: int
    notices: List[SimpleNotice]

@app.get("/health")
async def health():
    return {"status": "ok", "api_key": "set" if API_KEY else "missing"}

@app.get("/countries")
async def get_countries():
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

@app.get("/")
async def root():
    return FileResponse("index.html")

def build_ted_query(filters: Filters) -> str:
    parts = []
    if filters.text:
        parts.append(f'(notice-title ~ "{filters.text}")')
    if filters.country:
        codes = [c.strip().upper() for c in filters.country.split(",") if c.strip()]
        if codes:
            country_expr = " OR ".join([f'buyer-country = "{c}"' for c in codes])
            parts.append(f"({country_expr})")
    if filters.cpv_code:
        parts.append(f'(notice-title ~ "{filters.cpv_code}")')
    if filters.publication_date_from:
        d = filters.publication_date_from.replace("-", "")
        parts.append(f"(publication-date >= {d})")
    if filters.publication_date_to:
        d = filters.publication_date_to.replace("-", "")
        parts.append(f"(publication-date <= {d})")
    if filters.active_only:
        today = datetime.now().strftime("%Y%m%d")
        parts.append(f"(deadline-date-part >= {today})")
    if not parts:
        default_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        parts.append(f"(publication-date >= {default_date})")
    return " AND ".join(parts)

@app.post("/search", response_model=SearchResponse)
async def search_notices(req: SearchRequest):
    try:
        query = build_ted_query(req.filters) if req.filters else "(publication-date >= 20251101)"
        logger.info(f"TED Query: {query}")
        
        payload = {
            "query": query,
            "page": max(1, req.page),
            "limit": min(100, max(1, req.limit)),
            "scope": "ALL",
            "fields": SEARCH_FIELDS,
            "checkQuerySyntax": False,
            "paginationMode": "PAGE_NUMBER",
            "onlyLatestVersions": False
        }
        if API_KEY:
            payload["apiKey"] = API_KEY

        headers = {
            "Accept-Language": "en",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TED_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                text = resp.text[:500]
                logger.error(f"TED API error {resp.status_code}: {text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"TED API error {resp.status_code}: {text}",
                )

            data = resp.json()
            total = data.get("totalNoticeCount", 0)
            
            notices_out = []
            raw_notices = data.get("notices", [])
            logger.info(f"Raw notices count: {len(raw_notices)}")
            
            for i, item in enumerate(raw_notices):
                try:
                    notice = SimpleNotice(
                        publication_number=safe_extract(item.get("publication-number", "N/A")),
                        publication_date=safe_extract(item.get("publication-date")),
                        deadline_date=safe_extract(item.get("deadline-date-part")),
                        title=safe_extract(item.get("notice-title")),
                        buyer=safe_extract(item.get("buyer-name")),
                        country=safe_extract(item.get("buyer-country")),
                        city=safe_extract(item.get("organisation-city-buyer")),
                        cpv_code=""
                    )
                    notices_out.append(notice)
                    logger.debug(f"Parsed notice {i+1}: {notice.buyer[:50]}...")
                except Exception as parse_err:
                    logger.error(f"Parse error notice {i}: {parse_err}")
                    continue
            
            logger.info(f"Successfully parsed {len(notices_out)}/{len(raw_notices)} notices")
            return SearchResponse(total=total, notices=notices_out)
            
    except httpx.RequestError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error to TED API: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /search")
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8846"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
