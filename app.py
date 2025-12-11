"""
TED Scraper Backend - исправленная версия с поддержкой всех полей
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
API_KEY = os.getenv("TED_API_KEY", None)

# Полный список полей для поиска
SEARCH_FIELDS = [
    "publication-number",
    "publication-date",
    "deadline-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "city",
    "place-of-performance",
    "cpv-code",  # SKU/CPV код
    "procedure-type",
    "estimated-value",
    "estimated-value-currency",
    "buyer-email",
    "buyer-telephone",
    "buyer-website"
]

# Поля для детального просмотра
DETAIL_FIELDS = SEARCH_FIELDS + ["full-notice"]

class Filters(BaseModel):
    text: Optional[str] = None
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    country: Optional[str] = None
    cpv_code: Optional[str] = None  # SKU/CPV фильтр
    active_only: bool = False  # Только активные лоты

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
    performance_city: Optional[str] = None
    cpv_code: Optional[str] = None
    procedure_type: Optional[str] = None
    estimated_value: Optional[float] = None
    estimated_value_currency: Optional[str] = None

class SearchResponse(BaseModel):
    total: int
    notices: List[Notice]

class NoticeDetail(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    deadline_date: Optional[str] = None
    title: Optional[str] = None
    buyer: Dict[str, Any] = {}
    country: Optional[str] = None
    city: Optional[str] = None
    performance_city: Optional[str] = None
    cpv_code: Optional[str] = None
    procedure_type: Optional[str] = None
    estimated_value: Optional[float] = None
    estimated_value_currency: Optional[str] = None
    full_notice: Dict[str, Any] = {}
    direct_url: Optional[str] = None
    summary: Dict[str, Any] = {}

@app.get("/health")
async def health():
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}

@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")

def build_ted_query(filters: Filters) -> str:
    """Строит корректный запрос для API TED"""
    query_parts = []
    
    if filters.text:
        # Ищем в заголовке и описании
        query_parts.append(f'(notice-title ~ "{filters.text}" OR full-notice ~ "{filters.text}")')
    
    if filters.country:
        countries = [c.strip().upper() for c in filters.country.split(",") if c.strip()]
        if countries:
            country_query = " OR ".join([f'(buyer-country = {c})' for c in countries])
            query_parts.append(f"({country_query})")
    
    if filters.cpv_code:
        # Поиск по CPV коду (SKU)
        query_parts.append(f'(cpv-code = {filters.cpv_code.strip()})')
    
    # Даты публикации
    if filters.publication_date_from:
        from_date = filters.publication_date_from.replace("-", "")
        query_parts.append(f"(publication-date >= {from_date})")
    
    if filters.publication_date_to:
        to_date = filters.publication_date_to.replace("-", "")
        query_parts.append(f"(publication-date <= {to_date})")
    
    # Активные лоты (дедлайн в будущем)
    if filters.active_only:
        today = datetime.now().strftime("%Y%m%d")
        query_parts.append(f"(deadline-date >= {today})")
    
    if not query_parts:
        # По умолчанию - последние 30 дней
        default_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        query_parts.append(f"(publication-date >= {default_date})")
    
    return " AND ".join(query_parts)

@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        expert_query = build_ted_query(request.filters) if request.filters else "(publication-date >= 20240101)"
        
        logger.info(f"TED Query: {expert_query}")
        
        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "scope": "ALL",
            "fields": SEARCH_FIELDS,
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
            # Обрабатываем место выполнения (может быть строкой или объектом)
            place_of_performance = item.get("place-of-performance")
            performance_city = None
            
            if isinstance(place_of_performance, dict):
                performance_city = place_of_performance.get("city")
            elif isinstance(place_of_performance, str):
                performance_city = place_of_performance
            
            notice = Notice(
                publication_number=item.get("publication-number", "N/A"),
                publication_date=item.get("publication-date"),
                deadline_date=item.get("deadline-date"),
                title=item.get("notice-title", "No title"),
                buyer=item.get("buyer-name"),
                country=item.get("buyer-country"),
                city=item.get("city"),
                performance_city=performance_city,
                cpv_code=item.get("cpv-code"),
                procedure_type=item.get("procedure-type"),
                estimated_value=item.get("estimated-value"),
                estimated_value_currency=item.get("estimated-value-currency"),
            )
            notices.append(notice)
        
        return SearchResponse(total=total, notices=notices)
        
    except httpx.RequestError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notice/{publication_number}")
async def get_notice_details(publication_number: str):
    """Получение детальной информации о тендере"""
    try:
        query = f'(publication-number = "{publication_number}")'
        
        payload = {
            "query": query,
            "page": 1,
            "limit": 1,
            "scope": "ALL",
            "fields": DETAIL_FIELDS,
        }
        
        if API_KEY:
            payload["apiKey"] = API_KEY
        
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=30.0)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch notice details")
        
        data = response.json()
        notices = data.get("notices", [])
        
        if not notices:
            raise HTTPException(status_code=404, detail="Notice not found")
        
        item = notices[0]
        
        # Формируем детальный ответ
        detail = NoticeDetail(
            publication_number=item.get("publication-number"),
            publication_date=item.get("publication-date"),
            deadline_date=item.get("deadline-date"),
            title=item.get("notice-title"),
            buyer={
                "name": item.get("buyer-name"),
                "email": item.get("buyer-email"),
                "telephone": item.get("buyer-telephone"),
                "website": item.get("buyer-website"),
                "country": item.get("buyer-country"),
                "city": item.get("city")
            },
            country=item.get("buyer-country"),
            city=item.get("city"),
            performance_city=item.get("place-of-performance", {}).get("city") 
                          if isinstance(item.get("place-of-performance"), dict) 
                          else item.get("place-of-performance"),
            cpv_code=item.get("cpv-code"),
            procedure_type=item.get("procedure-type"),
            estimated_value=item.get("estimated-value"),
            estimated_value_currency=item.get("estimated-value-currency"),
            full_notice=item.get("full-notice", {}),
            direct_url=f"https://ted.europa.eu/udl?uri=TED:NOTICE:{publication_number}:TEXT:EN:HTML",
            summary={
                "type": item.get("procedure-type"),
                "country": item.get("buyer-country"),
                "procedure": item.get("procedure-type"),
                "lot": {
                    "title": item.get("notice-title"),
                    "description": item.get("full-notice", {}).get("description"),
                    "contract_nature": item.get("full-notice", {}).get("contract-nature"),
                    "classification": item.get("cpv-code"),
                    "place_of_performance": {
                        "city": item.get("place-of-performance", {}).get("city"),
                        "country": item.get("buyer-country")
                    },
                    "deadline": {
                        "date": item.get("deadline-date"),
                        "time": item.get("full-notice", {}).get("deadline-time", "")
                    }
                }
            }
        )
        
        return detail.dict()
        
    except Exception as e:
        logger.error(f"Detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/countries")
async def get_countries():
    """Полный список стран для выпадающего списка"""
    countries = [
        {"code": "AUT", "name": "Austria (Österreich)"},
        {"code": "BEL", "name": "Belgium (België/Belgique)"},
        {"code": "BGR", "name": "Bulgaria (България)"},
        {"code": "HRV", "name": "Croatia (Hrvatska)"},
        {"code": "CYP", "name": "Cyprus (Κύπρος)"},
        {"code": "CZE", "name": "Czech Republic (Česká republika)"},
        {"code": "DNK", "name": "Denmark (Danmark)"},
        {"code": "EST", "name": "Estonia (Eesti)"},
        {"code": "FIN", "name": "Finland (Suomi)"},
        {"code": "FRA", "name": "France"},
        {"code": "DEU", "name": "Germany (Deutschland)"},
        {"code": "GRC", "name": "Greece (Ελλάδα)"},
        {"code": "HUN", "name": "Hungary (Magyarország)"},
        {"code": "IRL", "name": "Ireland"},
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
        {"code": "ESP", "name": "Spain (España)"},
        {"code": "SWE", "name": "Sweden (Sverige)"},
        {"code": "GBR", "name": "United Kingdom"},
        {"code": "NOR", "name": "Norway (Norge)"},
        {"code": "CHE", "name": "Switzerland (Schweiz/Suisse)"},
        {"code": "ISL", "name": "Iceland (Ísland)"},
        {"code": "LIE", "name": "Liechtenstein"},
        {"code": "MKD", "name": "North Macedonia (Северна Македонија)"},
        {"code": "SRB", "name": "Serbia (Србија)"},
        {"code": "TUR", "name": "Turkey (Türkiye)"},
        {"code": "UKR", "name": "Ukraine (Україна)"},
        {"code": "ALB", "name": "Albania (Shqipëria)"},
        {"code": "BIH", "name": "Bosnia and Herzegovina (Bosna i Hercegovina)"},
        {"code": "MDA", "name": "Moldova (Republica Moldova)"},
        {"code": "MNE", "name": "Montenegro (Crna Gora)"},
    ]
    return countries

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)