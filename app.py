"""
TED Scraper Backend с Accordion функциональностью
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
API_KEY = os.getenv("TED_API_KEY", None)
PREFERRED_LANGS = ["eng", "deu", "fra"]

# Поля для списка результатов (минимальный набор)
SEARCH_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "organisation-country-buyer",
    "organisation-city-buyer",
    "place-of-performance-city-lot",
    "deadline-receipt-tender-date-lot",
]

# Расширенные поля для детального просмотра
DETAIL_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "notice-type",
    "organisation-name-buyer",
    "buyer-email",
    "organisation-city-buyer",
    "organisation-country-buyer",
    "place-of-performance-city-lot",
    "place-of-performance-country-lot",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request-date-lot",
    "deadline-receipt-expressions-date-lot",
    "deadline-receipt-tender-time-lot",
    "contract-nature",
    "description-lot",
    "title-lot",
    "contract-duration-start-date-lot",
    "contract-duration-end-date-lot",
    "document-url-lot",
    "document-restricted-lot",
    "estimated-value-cur-lot",
    "main-classification-lot",
    "procedure-type",
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
    deadline_date: Optional[str] = None
    title: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    performance_city: Optional[str] = None


class SearchResponse(BaseModel):
    total: int
    notices: List[Notice]


class NoticeDetail(BaseModel):
    publication_number: str
    direct_url: str
    summary: dict
    full_notice: dict


@app.get("/health")
async def health():
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}


@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")


def extract_multilang_field(field_value: Any, default: str = "N/A") -> str:
    """Извлекает значение из многоязычного поля TED"""
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
    """Нормализует дату в формат YYYY-MM-DD"""
    if not date_str or not isinstance(date_str, str):
        return None
    return date_str[:10]


def normalize_time(time_str: Optional[str]) -> Optional[str]:
    """Извлекает время из строки формата '23:59:00 (UTC+01:00)'"""
    if not time_str or not isinstance(time_str, str):
        return None
    # Берём только первую часть до пробела
    return time_str.split()[0] if ' ' in time_str else time_str


def get_deadline_date(item: dict) -> Optional[str]:
    """Получает дедлайн из доступных полей"""
    for field_name in [
        "deadline-receipt-tender-date-lot",
        "deadline-receipt-request-date-lot",
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
            expert_query = "(publication-date >= 19930101)"
        else:
            expert_query = " AND ".join(query_terms)

        logger.info(f"POST /search: query={expert_query}")

        payload = {
            "query": expert_query,
            "page": max(1, request.page),
            "limit": min(100, max(1, request.limit)),
            "fields": SEARCH_FIELDS,
        }

        if API_KEY:
            payload["apiKey"] = API_KEY

        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)

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

        notices: List[Notice] = []
        for item in notices_data:
            notice = Notice(
                publication_number=item.get("publication-number", "N/A"),
                publication_date=normalize_date(item.get("publication-date")),
                deadline_date=get_deadline_date(item),
                title=extract_multilang_field(item.get("notice-title"), "No title"),
                country=extract_multilang_field(item.get("organisation-country-buyer"), "Unknown"),
                city=extract_multilang_field(item.get("organisation-city-buyer"), ""),
                performance_city=extract_multilang_field(item.get("place-of-performance-city-lot"), ""),
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


@app.get("/notice/{publication_number}")
async def get_notice_detail(publication_number: str):
    """Получает детальную информацию о notice"""
    try:
        logger.info(f"GET /notice/{publication_number}")

        query = f"(publication-number = {publication_number})"
        payload = {
            "query": query,
            "page": 1,
            "limit": 1,
            "fields": DETAIL_FIELDS,
        }

        if API_KEY:
            payload["apiKey"] = API_KEY

        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=120.0)

        if response.status_code != 200:
            error_detail = response.json().get("message", response.text[:200]) if response.content else "No response"
            raise HTTPException(status_code=response.status_code, detail=f"TED API error: {error_detail}")

        data = response.json()
        notices = data.get("notices", [])

        if not notices:
            raise HTTPException(status_code=404, detail=f"Notice {publication_number} not found")

        item = notices[0]

        # Direct URL
        direct_url = f"https://ted.europa.eu/en/notice/-/detail/{publication_number}"

        # Summary
        deadline_date = get_deadline_date(item)
        deadline_time = normalize_time(extract_multilang_field(item.get("deadline-receipt-tender-time-lot"), ""))
        
        summary = {
            "type": extract_multilang_field(item.get("notice-type"), "Competition"),
            "title": extract_multilang_field(item.get("notice-title"), "No title"),
            "country": extract_multilang_field(item.get("organisation-country-buyer"), "Unknown"),
            "procedure_type": extract_multilang_field(item.get("procedure-type"), "N/A"),
            "buyer": {
                "name": extract_multilang_field(item.get("organisation-name-buyer"), "N/A"),
                "email": extract_multilang_field(item.get("buyer-email"), "N/A"),
                "city": extract_multilang_field(item.get("organisation-city-buyer"), "N/A"),
                "country": extract_multilang_field(item.get("organisation-country-buyer"), "N/A"),
            },
            "lot": {
                "title": extract_multilang_field(item.get("title-lot"), "LOT-0000"),
                "description": extract_multilang_field(item.get("description-lot"), "N/A"),
                "contract_nature": extract_multilang_field(item.get("contract-nature"), "N/A"),
                "classification": extract_multilang_field(item.get("main-classification-lot"), "N/A"),
                "place_of_performance": {
                    "city": extract_multilang_field(item.get("place-of-performance-city-lot"), "N/A"),
                    "country": extract_multilang_field(item.get("place-of-performance-country-lot"), "N/A"),
                },
                "start_date": normalize_date(item.get("contract-duration-start-date-lot")),
                "end_date": normalize_date(item.get("contract-duration-end-date-lot")),
                "deadline": {
                    "date": deadline_date,
                    "time": deadline_time,
                },
            },
        }

        # Full Notice (все доступные поля)
        full_notice = {k: extract_multilang_field(v, "N/A") for k, v in item.items()}

        return NoticeDetail(
            publication_number=publication_number,
            direct_url=direct_url,
            summary=summary,
            full_notice=full_notice,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notice detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/static", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
