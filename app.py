"""
TED Scraper - BULLETPROOF VERSION 6.0
Maximum error handling and validation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
from datetime import datetime
import traceback

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
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
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class NoticeItem(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    notice_type: Optional[str] = None
    buyer_name: Optional[str] = None
    title: Optional[str] = None
    cpv_codes: Optional[str] = None
    country: Optional[str] = None
    url: Optional[str] = None


class SearchResponse(BaseModel):
    total_notices: int = 0
    total_pages: int = 0
    current_page: int = 1
    page_size: int = 10
    notices: List[NoticeItem] = []
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    ted_api_available: bool
    timestamp: datetime


# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(
    title="TED Scraper - v6.0 BULLETPROOF",
    version="6.0.0",
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
except Exception as e:
    logger.warning(f"Could not mount static: {e}")

# ============================================================================
# FUNCTIONS
# ============================================================================

async def call_ted_api(query_text: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Call TED API with REQUIRED fields parameter"""
    
    try:
        logger.info(f"=== TED API CALL START ===")
        logger.info(f"Query: {query_text}, Page: {page}, Limit: {limit}")
        
        # REQUIRED FIELDS
        fields = [
            "publication-number",
            "notice-title",
            "buyer-name",
            "publication-date",
            "notice-type",
            "cpv-code",
            "place-of-performance"
        ]
        
        payload = {
            "query": query_text,
            "page": page,
            "limit": limit,
            "scope": "ACTIVE",
            "fields": fields
        }
        
        logger.info(f"Payload prepared: {len(payload)} keys")
        
        async with httpx.AsyncClient(timeout=60, verify=True) as client:
            logger.info(f"Sending POST to: https://api.ted.europa.eu/v3/notices/search")
            
            response = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:1000]
                logger.error(f"API error: {error_text}")
                raise Exception(f"API returned {response.status_code}")
            
            data = response.json()
            logger.info(f"✓ Got response with {len(data.get('results', []))} results")
            logger.info(f"=== TED API CALL END ===")
            
            return data
            
    except Exception as e:
        logger.error(f"❌ TED API Error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def parse_results(response_data: Dict[str, Any]) -> List[NoticeItem]:
    """Parse results safely"""
    notices = []
    
    try:
        results = response_data.get("results", [])
        logger.info(f"Parsing {len(results)} results...")
        
        for i, item in enumerate(results):
            try:
                pub_num = str(item.get("publication-number", "N/A"))
                
                notice = NoticeItem(
                    publication_number=pub_num,
                    publication_date=item.get("publication-date"),
                    notice_type=item.get("notice-type"),
                    buyer_name=item.get("buyer-name"),
                    title=item.get("notice-title"),
                    cpv_codes=item.get("cpv-code"),
                    country=item.get("place-of-performance"),
                    url=f"https://ted.europa.eu/en/notice/{pub_num}"
                )
                notices.append(notice)
                
            except Exception as e:
                logger.warning(f"Could not parse result {i}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(notices)} notices")
        return notices
        
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Serve frontend"""
    try:
        index_path = os.path.join(os.path.dirname(__file__), "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Root error: {e}")
        return {"error": str(e)}, 500


@app.get("/{path:path}")
async def serve_files(path: str):
    """Serve static files"""
    try:
        if path.startswith("static/"):
            fpath = os.path.join(os.path.dirname(__file__), path)
            if os.path.exists(fpath):
                return FileResponse(fpath)
        
        index_path = os.path.join(os.path.dirname(__file__), "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        raise HTTPException(status_code=404)
    except Exception as e:
        logger.error(f"Serve files error: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check"""
    logger.info("Health check requested")
    
    ted_ok = False
    try:
        await call_ted_api("*", 1, 1)
        ted_ok = True
        logger.info("✓ TED API is available")
    except Exception as e:
        logger.warning(f"⚠ TED API not available: {str(e)[:50]}")
    
    return HealthResponse(
        status="healthy" if ted_ok else "degraded",
        ted_api_available=ted_ok,
        timestamp=datetime.now()
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for tenders"""
    logger.info("=" * 70)
    logger.info("SEARCH ENDPOINT CALLED")
    logger.info("=" * 70)
    
    try:
        logger.info(f"Request received:")
        logger.info(f"  Filters: {request.filters}")
        logger.info(f"  Page: {request.page}")
        logger.info(f"  Page size: {request.page_size}")
        
        # Build query
        query = "*"
        if request.filters.full_text:
            query = request.filters.full_text.strip()
            logger.info(f"Using query: {query}")
        
        logger.info(f"Calling TED API...")
        
        # Call API
        ted_data = await call_ted_api(query, request.page, request.page_size)
        logger.info(f"TED API returned successfully")
        
        # Parse
        logger.info(f"Parsing results...")
        notices = parse_results(ted_data)
        logger.info(f"Got {len(notices)} parsed notices")
        
        # Calculate pages
        total = ted_data.get("total", 0)
        total_pages = max(1, (total + request.page_size - 1) // request.page_size)
        
        logger.info(f"Total: {total}, Pages: {total_pages}")
        
        response = SearchResponse(
            total_notices=total,
            total_pages=total_pages,
            current_page=request.page,
            page_size=request.page_size,
            notices=notices,
            timestamp=datetime.now()
        )
        
        logger.info(f"✓ Search completed successfully")
        logger.info("=" * 70)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ SEARCH ERROR: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 70)
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/notice/{notice_id}")
async def get_notice(notice_id: str):
    """Get notice details"""
    try:
        logger.info(f"Getting notice: {notice_id}")
        
        ted_data = await call_ted_api(f'publication-number:{notice_id}', 1, 1)
        notices = parse_results(ted_data)
        
        if not notices:
            raise HTTPException(status_code=404, detail="Not found")
        
        return notices[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Notice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def universal_exception_handler(request, exc):
    """Catch all exceptions"""
    logger.error(f"UNHANDLED EXCEPTION: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    return {"error": str(exc)}, 500


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 TED SCRAPER v6.0 - BULLETPROOF")
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
        log_level="info"
    )
