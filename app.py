"""
TED Scraper - FINAL WORKING VERSION 3.0
Direct query to TED API v3.0 - NO preprocessing, simple format
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import logging
from datetime import datetime, date
import json
from enum import Enum
import os

# ============================================================================
# CONFIG
# ============================================================================

TED_API_BASE_URL = "https://api.ted.europa.eu/v3/notices/search"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# ============================================================================
# MODELS
# ============================================================================

class SearchFilters(BaseModel):
    full_text: Optional[str] = None
    cpv_codes: Optional[List[str]] = None
    buyer_countries: Optional[List[str]] = None
    publication_date_from: Optional[date] = None
    publication_date_to: Optional[date] = None


class SearchRequest(BaseModel):
    filters: SearchFilters = Field(...)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    scope: str = Field("ACTIVE")


class NoticeItem(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    notice_type: Optional[str] = None
    buyer_name: Optional[str] = None
    title: Optional[str] = None
    cpv_codes: Optional[List[str]] = None
    country: Optional[str] = None
    url: Optional[str] = None


class SearchResponse(BaseModel):
    total_notices: int
    total_pages: int
    current_page: int
    page_size: int
    notices: List[NoticeItem]
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    ted_api_available: bool
    timestamp: datetime


# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(
    title="TED Scraper v3.0",
    version="3.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(static_dir):
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    except:
        pass

# ============================================================================
# FUNCTIONS
# ============================================================================

def build_query(filters: SearchFilters) -> str:
    """
    Build simple query for TED API v3.0
    TED API accepts very simple format - just keywords and field:value pairs
    """
    parts = []
    
    # Simple keyword search
    if filters.full_text:
        parts.append(filters.full_text)
    
    # If nothing, return wildcard
    if not parts:
        return "*"
    
    return " ".join(parts)


def parse_results(data: Dict[str, Any]) -> List[NoticeItem]:
    """Parse TED API response"""
    notices = []
    
    for notice in data.get("results", []):
        try:
            pub_num = notice.get("publication-number", "N/A")
            
            item = NoticeItem(
                publication_number=pub_num,
                publication_date=notice.get("publication-date"),
                notice_type=notice.get("notice-type"),
                buyer_name=notice.get("buyer-name"),
                title=notice.get("notice-title"),
                cpv_codes=notice.get("cpv-code"),
                country=notice.get("place-of-performance"),
                url=f"https://ted.europa.eu/en/notice/{pub_num}" if pub_num != "N/A" else None,
            )
            notices.append(item)
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            continue
    
    return notices


async def call_ted_api(query: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """
    Call TED API v3.0 with SIMPLE query
    Endpoint: POST https://api.ted.europa.eu/v3/notices/search
    """
    
    # MINIMAL request body - only required fields
    request_body = {
        "query": query,
        "page": page,
        "limit": page_size,
        "scope": "ACTIVE"
    }
    
    logger.info(f"🔍 Query: {query}")
    logger.info(f"📤 POST to: {TED_API_BASE_URL}")
    logger.debug(f"Body: {json.dumps(request_body)}")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                TED_API_BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text[:300]}")
                response.raise_for_status()
            
            data = response.json()
            total = data.get("total", 0)
            count = len(data.get("results", []))
            
            logger.info(f"✓ Got {count} results from {total} total")
            return data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        raise HTTPException(status_code=502, detail=f"TED API: {e.response.reason_phrase}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok"}


@app.get("/{path:path}")
async def serve_files(path: str):
    if path.startswith("static/"):
        fpath = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(fpath):
            return FileResponse(fpath)
    
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    raise HTTPException(status_code=404)


@app.get("/health", response_model=HealthResponse)
async def health():
    ted_ok = False
    try:
        await call_ted_api("*", 1, 1)
        ted_ok = True
    except:
        pass
    
    return HealthResponse(
        status="healthy" if ted_ok else "degraded",
        ted_api_available=ted_ok,
        timestamp=datetime.now()
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    logger.info(f"Search request: {request.filters}")
    
    try:
        query = build_query(request.filters)
        logger.info(f"Built query: {query}")
        
        ted_response = await call_ted_api(query, request.page, request.page_size)
        
        notices = parse_results(ted_response)
        total = ted_response.get("total", 0)
        total_pages = (total + request.page_size - 1) // request.page_size
        
        logger.info(f"Returning {len(notices)} notices")
        
        return SearchResponse(
            total_notices=total,
            total_pages=total_pages,
            current_page=request.page,
            page_size=request.page_size,
            notices=notices,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notice/{notice_id}")
async def get_notice(notice_id: str):
    try:
        ted_response = await call_ted_api(f'publication-number:{notice_id}', 1, 1)
        notices = parse_results(ted_response)
        
        if not notices:
            raise HTTPException(status_code=404, detail="Not found")
        
        return notices[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 TED SCRAPER v3.0 - SIMPLIFIED VERSION")
    print("="*60)
    print("Frontend: http://localhost:8846")
    print("API: http://localhost:8846/api/docs")
    print("Health: http://localhost:8846/health")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8846,
        reload=False,
        log_level="info"
    )
