"""
TED Scraper Backend – версия с поддержкой разных полей deadline
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Any
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

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

# добавляем несколько вариантов полей для дедлайна
SUPPORTED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "organisation-country-buyer",
    "organisation-city-buyer",
    "place-of-performance-city-lot",
    "deadline-receipt-tender-date-lot",      # BT-131(d) - основной дедлайн
    "deadline-receipt-requests",              # BT-1311 - дедлайн для заявок на участие
    "deadline-receipt-expressions-date-lot",  # дедлайн для выражения заинтересованности
]

API_KEY = os.getenv("TED_API_KEY", None)

PREFERRED_LANGS = ["eng", "deu", "fra"]


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
    deadline_date: Optional[str] = None
    title: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    performance_city: Optional[str] = None


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
    Извлекает значение из многоязычного поля TED.
    Приоритет: eng -> deu -> fra -> любой первый доступный.
    """
    if isinstance(field_value, str):
        return field_value

    if isinstance(field_value, dict):
        for lang in PREFERRED_LANGS:
            if lang in field_value:
                val = field_value[lang]
                if isinstance(val, list) and val:
                    return val[0]
                if isinstance(val, str):
                    return val
        for val in field_value.values():
            if isinstance(val, list) and val:
                return val[0]
            if isinstance(val, str):
                return val

    if isinstance(field_value, list) and field_value:
        return field_value[0] if isinstance(field_value[0], str) else str(field_value[0])

    return default


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    TED часто отдаёт даты как '2025-09-30+02:00'.
    Берём только первые 10 символов 'YYYY-MM-DD'.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    return date_str[:10]


def get_deadline_date(item: dict) -> Optional[str]:
    """
    Пытается получить дедлайн из нескольких возможных полей.
    Приоритет:
    1. deadline-receipt-tender-date-lot (основной дедлайн для подачи тендеров)
    2. deadline-receipt-requests (дедлайн для заявок на участие)
    3. deadline-receipt-expressions-date-lot (дедлайн для выражения заинтересованности)
    """
    # пробуем разные варианты
    for field_name in [
        "deadline-receipt-tender-date-lot",
        "deadline-receipt-requests", 
        "deadline-receipt-expressions-date-lot"
    ]:
        value = item.get(field_name)
        if value:
            normalized = normalize_date(value)
            if normalized:
                return normalized
    return None


@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        query_terms = []

        if request.filters:
            if request.filters.text:
                text = request.filters.text.strip()
                ft_term = f'(notice-title ~ "{text}")'
                query_terms.append(ft_term)

            if request.filters.country:
                countries = [
                    c.strip().upper()
                    for c in request.filters.country.split(",")
                    if c.strip()
                ]
                if countries:
                    if len(countries) == 1:
                        query_terms.append(f"(organisation-country-buyer = {countries[0]})")
                    else:
                        or_terms = " OR ".join(
                            f"(organisation-country-buyer = {c})" for c in countries
                        )
                        query_terms.append(f"({or_terms})")

            if request.filters.publication_date_from:
                from_date = request.filters.publication_date_from.replace("-", "")
                if from_date:
                    query_terms.append(f"(publication-date >= {from_date})")

            if request.filters.publication_date_to:
                to_date = request.filters.publication_date_to.replace("-", "")
                if to_date:
                    query_terms.append(f"(publication-date <= {to_date})")

        if not query_terms:
            expert_query = get_historical_broad()
        else:
            expert_query = " AND ".join(query_terms)

        logger.info(
            f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}"
        )

        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "fields": SUPPORTED_FIELDS,
        }

        if API_KEY:
            payload["apiKey"] = API_KEY

        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)

        logger.info(f"Response status: {response.status_code}")

        if response.status_code != 200:
            error_detail = (
                response.json().get("message", response.text[:200])
                if response.content
                else "No response"
            )
            logger.error(f"TED Error ({response.status_code}): {error_detail}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"TED API error: {error_detail}",
            )

        data = response.json()
        notices_data = data.get("notices", [])
        total = data.get("total", len(notices_data))

        logger.info(f"Total results: {total} notices")
        logger.info(f"Received {len(notices_data)} notices in response")

        notices: List[Notice] = []
        for item in notices_data:
            notice = Notice(
                publication_number=item.get("publication-number", "N/A"),
                publication_date=normalize_date(item.get("publication-date")),
                deadline_date=get_deadline_date(item),  # используем новую функцию
                title=extract_multilang_field(
                    item.get("notice-title"), "No title"
                ),
                country=extract_multilang_field(
                    item.get("organisation-country-buyer"), "Unknown"
                ),
                city=extract_multilang_field(
                    item.get("organisation-city-buyer"), ""
                ),
                performance_city=extract_multilang_field(
                    item.get("place-of-performance-city-lot"), ""
                ),
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
