"""
TED Scraper Backend - search + notice details with multilang handling
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

PREFERRED_LANGS = ["eng", "fra", "deu"]

SEARCH_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
]

DETAIL_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "place-of-performance-country-lot",
    "place-of-performance-city-lot",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
    "contract-nature",
    "description-lot",
    "title-lot",
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


class NoticeDetail(BaseModel):
    publication_number: str
    direct_url: str
    summary: dict
    full_notice: dict


def extract_multilang_field(field_value: Any, default: str = "N/A") -> str:
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
        first = field_value[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return extract_multilang_field(first, default)

    return default


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str or not isinstance(date_str, str):
        return None
    return date_str[:10]


def normalize_time(time_str: Optional[str]) -> Optional[str]:
    if not time_str or not isinstance(time_str, str):
        return None
    return time_str.split()[0] if " " in time_str else time_str


def get_historical_broad() -> str:
    return "(publication-date >= 19930101)"


def get_test_query() -> str:
    return "buyer-country = FRA"


@app.get("/health")
async def health():
    return {"status": "ok", "api_key": "set" if API_KEY else "missing (limited access)"}


@app.get("/")
async def read_root():
    if not os.path.exists("index.html"):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse("index.html")


@app.post("/search")
async def search_notices(request: SearchRequest):
    try:
        query_terms: List[str] = []
        has_date_filter = False

        if request.filters:
            if request.filters.text:
                text = request.filters.text.strip()
                ft_term = f'(notice-title ~ "{text}")'
                query_terms.append(ft_term)

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

