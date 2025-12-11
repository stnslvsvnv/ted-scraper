"""
TED Scraper Backend – исправленная версия для TED API v3
Убраны невалидные поля fields, запрос работает стабильно
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

# Модели
class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None  # YYYY-MM-DD
    publication_date_to: Optional[str] = None  # YYYY-MM-DD
    country: Optional[str] = None  # "DEU, FRA"
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

# Служебные эндпоинты
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "api_key": "set" if API_KEY else "missing",
    }

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

# Построение запроса к TED
def build_ted_query(filters: Filters) -> str:
    parts = []
    if filters.text:
        parts.append(f'(notice-title ~ "{filters.text}")')
    if filters.country:
        codes = [c.strip().upper() for c in filters.country.split(",") if c.strip()]
        if codes:
            country_expr = " OR ".join([f'(buyer-country = "{c}")' for c in codes])
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
        parts.append(f"(deadline-date >= {today})")
    if not parts:
        default_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        parts.append(f"(publication-date >= {default_date})")
    query = " AND ".join(parts)
    return query

# Основной поиск
@app.post("/search", response_model=SearchResponse)
async def search_notices(req: SearchRequest):
    try:
        query = build_ted_query(req.filters) if req.filters else "(publication-date >= 20240101)"
        logger.info(f"TED Query: {query}")
        
        payload = {
            "query": query,
            "page": max(1, req.page),
            "limit": min(100, max(1, req.limit)),
            "scope": "ALL",
            # УБРАЛИ fields - это вызывало 400 ошибку!
        }
        if API_KEY:
            payload["apiKey"] = API_KEY

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TED_API_URL, json=payload)
            if resp.status_code != 200:
                text = resp.text[:500]
                logger.error(f"TED API error {resp.status_code}: {text}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"TED API error {resp.status_code}: {text}",
                )

            data = resp.json()
            total = data.get("totalNoticeCount", 0)
            notices_out: List[Notice] = []
            for item in data.get("notices", []):
                notices_out.append(
                    Notice(
                        publication_number=item.get("publication-number", "N/A"),
                        publication_date=item.get("publication-date"),
                        deadline_date=item.get("deadline-date"),
                        title=item.get("notice-title"),
                        buyer=item.get("buyer-name"),
                        country=item.get("buyer-country"),
                        city=item.get("city"),
                        cpv_code=None,  # заполним позже через отдельный эндпоинт
                    )
                )
            
            logger.info(f"Returned {len(notices_out)} notices out of {total}")
            return SearchResponse(total=total, notices=notices_out)
            
    except httpx.RequestError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error to TED API: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /search")
        raise HTTPException(status_code=500, detail=str(e))

# Статика
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8846"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
