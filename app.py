"""
TED Scraper - FINAL WORKING VERSION 5.0
WITH REQUIRED FIELDS FIX
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ============================================================================
# MODELS
# ============================================================================

class SearchFilters(BaseModel):
    full_text: Optional[str] = None
    cpv_codes: Optional[List[str]] = None
    buyer_countries: Optional[List[str]] = None
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None


class SearchRequest(BaseModel):
    filters: SearchFilters
    page: int = 1
    page_size: int = 10


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
    total_notices: int = 0
    total_pages: int = 0
    current_page: int = 1
    page_size: int = 10
    notices: List[NoticeItem] = []
    timestamp: datetime = None

    class Config:
        default_factory = datetime.now


class HealthResponse(BaseModel):
    status: str
    ted_api_available: bool
    timestamp: datetime


# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(
    title="TED Scraper - v5.0 WORKING",
    version="5.0.0",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except:
    pass

# ============================================================================
# FUNCTIONS
# ============================================================================

async def call_ted_api(query_text: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """
    Call TED API v3.0 - FIXED VERSION WITH REQUIRED FIELDS
    
    IMPORTANT: TED API requires "fields" parameter to be non-empty!
    """
    
    # REQUIRED FIELDS - MUST NOT BE EMPTY!
    fields = [
        "publication-number",
        "notice-title",
        "buyer-name",
        "publication-date",
        "notice-type",
        "cpv-code",
        "place-of-performance"
    ]
    
    # Request body with REQUIRED fields parameter
    payload = {
        "query": query_text,
        "page": page,
        "limit": limit,
        "scope": "ACTIVE",
        "fields": fields  # ← REQUIRED! MUST NOT BE EMPTY!
    }
    
    logger.info(f"🚀 TED API Call")
    logger.info(f"   Endpoint: https://api.ted.europa.eu/v3/notices/search")
    logger.info(f"   Query: {query_text}")
    logger.info(f"   Page: {page}, Limit: {limit}")
    logger.info(f"   Fields: {len(fields)} fields")
    logger.debug(f"   Payload: {payload}")
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            logger.info(f"   Sending POST request...")
            
            response = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            logger.info(f"   Response Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"   Error Body: {response.text[:500]}")
                raise HTTPException(
                    status_code=502,
                    detail=f"TED API returned {response.status_code}: {response.reason_phrase}"
                )
            
            data = response.json()
            logger.info(f"   ✓ Success!")
            logger.info(f"   Total results: {data.get('total', 0)}")
            logger.info(f"   Results on page: {len(data.get('results', []))}")
            
            return data
            
    except httpx.TimeoutException:
        logger.error("   ❌ Timeout!")
        raise HTTPException(status_code=502, detail="TED API timeout")
    except httpx.RequestError as e:
        logger.error(f"   ❌ Request error: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def parse_results(response_data: Dict[str, Any]) -> List[NoticeItem]:
    """Parse TED API response"""
    notices = []
    
    for item in response_data.get("results", []):
        try:
            pub_num = item.get("publication-number", "N/A")
            notice = NoticeItem(
                publication_number=pub_num,
                publication_date=item.get("publication-date"),
                notice_type=item.get("notice-type"),
                buyer_name=item.get("buyer-name"),
                title=item.get("notice-title"),
                cpv_codes=item.get("cpv-code"),
                country=item.get("place-of-performance"),
                url=f"https://ted.europa.eu/en/notice/{pub_num}" if pub_num != "N/A" else None,
            )
            notices.append(notice)
        except Exception as e:
            logger.warning(f"Parse error on item: {e}")
            continue
    
    return notices


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Serve frontend"""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "api_available": True}


@app.get("/{path:path}")
async def serve_files(path: str):
    """Serve static files"""
    if path.startswith("static/"):
        fpath = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(fpath):
            return FileResponse(fpath)
    
    # Fallback to index
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check"""
    logger.info("🏥 Health check")
    
    ted_ok = False
    try:
        logger.info("   Testing TED API...")
        await call_ted_api("*", 1, 1)
        ted_ok = True
        logger.info("   ✓ TED API OK")
    except Exception as e:
        logger.warning(f"   ⚠ TED API error: {str(e)[:100]}")
    
    return HealthResponse(
        status="healthy" if ted_ok else "degraded",
        ted_api_available=ted_ok,
        timestamp=datetime.now()
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for tenders"""
    logger.info("=" * 60)
    logger.info("📝 SEARCH REQUEST")
    logger.info("=" * 60)
    logger.info(f"Filters: {request.filters}")
    logger.info(f"Page: {request.page}, Size: {request.page_size}")
    
    try:
        # Build simple query
        query = "*"
        if request.filters.full_text:
            query = request.filters.full_text
            logger.info(f"Using text filter: {query}")
        
        # Call API
        logger.info("Calling TED API...")
        ted_data = await call_ted_api(query, request.page, request.page_size)
        
        # Parse
        notices = parse_results(ted_data)
        total = ted_data.get("total", 0)
        total_pages = (total + request.page_size - 1) // request.page_size
        
        logger.info(f"Parsed {len(notices)} notices")
        logger.info("=" * 60)
        
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
        logger.error(f"❌ SEARCH ERROR: {str(e)}")
        logger.error("=" * 60)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notice/{notice_id}")
async def get_notice(notice_id: str):
    """Get notice details"""
    try:
        ted_data = await call_ted_api(f'publication-number:{notice_id}', 1, 1)
        notices = parse_results(ted_data)
        
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
    
    print("\n" + "="*70)
    print("🚀 TED SCRAPER v5.0 - WORKING VERSION")
    print("="*70)
    print("Frontend: http://localhost:8846")
    print("API: http://localhost:8846/api/docs")
    print("Health: http://localhost:8846/health")
    print("="*70 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8846,
        reload=False,
        log_level="debug"
    )
