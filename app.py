"""
TED Scraper Backend - стабильная минимальная версия поиска
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

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"
API_KEY = os.getenv("TED_API_KEY", None)

SUPPORTED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
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
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}


@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")


def get_historical_broad() -> str:
    return "(publication-date >= 19930101)"


@app.post("/search")
async def search_notices(request: SearchRequest):
    query_terms = []
    has_date_filter = False

    if request.filters:
        if request.filters.text:
            text = request.filters.text.strip()
            query_terms.append(f'(notice-title ~ "{text}")')

        if request.filters.country:
            country = request.filters.country.strip().upper()
            query_terms.append(f"(buyer-country = {country})")

        if request.filters.publication_date_from:
            from_date = request.filters.publication_date_from.replace("-", "")
            if from_date:
                query_terms.append(f"(publication-date >= {from_date})")
                has_date_filter = True

        if request.filters.publication_date_to:
            to_date = request.filters.publication_date_to.replace("-", "")
            if to_date:
                query_terms.append(f"(publication-date <= {to_date})")
                has_date_filter = True

    if not query_terms:
        expert_query = get_historical_broad()
    else:
        expert_query = " AND ".join(query_terms)

    if (
        has_date_filter
        and (not request.filters or not request.filters.text)
        and (not request.filters or not request.filters.country)
    ):
        expert_query = f"{get_historical_broad()} AND {expert_query}"

    logger.info(
        f"POST /search: query={expert_query}, page={request.page}, limit={request.limit}"
    )

    payload = {
        "query": expert_query,
        "page": max(1, request.page),
        "limit": min(100, max(1, request.limit)),
        "scope": "ALL",
        "fields": SUPPORTED_FIELDS,
    }

    if API_KEY:
        payload["apiKey"] = API_KEY

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(TED_API_URL, json=payload, timeout=60.0)

        if response.status_code != 200:
            detail = (
                response.json().get("message", response.text[:200])
                if response.content
                else "No response"
            )
            logger.error(f"TED API error {response.status_code}: {detail}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"TED API error: {detail}",
            )

        data = response.json()
        total = data.get("totalNoticeCount", data.get("total", 0)) or 0

        notices: List[Notice] = []
        for item in data.get("notices", data.get("results", [])):
            notices.append(
                Notice(
                    publication_number=item.get("publication-number", "N/A"),
                    publication_date=item.get("publication-date"),
                    title=item.get("notice-title", "No title"),
                    buyer=item.get("buyer-name", "Unknown buyer"),
                    country=item.get("buyer-country", "Unknown"),
                )
            )

        logger.info(f"Returned {len(notices)} notices out of {total}")
        return SearchResponse(total=int(total), notices=notices)

    except httpx.RequestError as e:
        logger.error(f"TED connection error: {e}")
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
