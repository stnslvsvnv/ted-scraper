"""
TED Scraper Backend - CORRECT VERSION
Fixes:
1. fields = ["CONTENT"] only (supported field)
2. Accept query directly from frontend
3. Return { total, results } format
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tedapi")

# ============================================================================
# MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str  # Already formatted query string from frontend
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
    results: List[Notice]


# ============================================================================
# APP
# ============================================================================

app = FastAPI(title="TED API Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
except:
    pass

# ============================================================================
# BACKEND LOGIC
# ============================================================================

async def search_ted_api(query: str, page: int = 1, limit: int = 25) -> Dict[str, Any]:
    """
    Call TED API v3.0
    
    FIX 1: Use only supported field "CONTENT"
    FIX 2: Accept pre-formatted query from frontend (dates already in YYYYMMDD)
    """
    
    logger.info(f"🔍 TED API Query: {query}")
    logger.info(f"   Page: {page}, Limit: {limit}")
    
    # FIX 1: Use ONLY supported field
    fields = ["CONTENT"]
    
    payload = {
        "query": query,
        "page": page,
        "limit": limit,
        "scope": "ACTIVE",
        "fields": fields
    }
    
    logger.info(f"📤 POST to https://api.ted.europa.eu/v3/notices/search")
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"📥 Status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:1000]
                logger.error(f"❌ API Error: {error_text}")
                raise Exception(f"API {response.status_code}: {error_text}")
            
            data = response.json()
            logger.info(f"✓ Total: {data.get('total', 0)}, Results: {len(data.get('results', []))}")
            
            return data
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise


def parse_notices(ted_response: Dict[str, Any]) -> List[Notice]:
    """Parse TED API response with CONTENT field"""
    notices = []
    
    for item in ted_response.get("results", []):
        try:
            # CONTENT field contains XML/JSON with notice data
            content = item.get("CONTENT", {})
            
            # Extract from CONTENT if it's a dict, otherwise use item directly
            if isinstance(content, dict):
                data = content
            else:
                data = item
            
            notice = Notice(
                publication_number=data.get("publication-number") or data.get("ND-Root") or "N/A",
                publication_date=data.get("publication-date"),
                title=data.get("notice-title") or data.get("title"),
                buyer=data.get("buyer-name") or data.get("organisation-name"),
                country=data.get("place-of-performance") or data.get("country")
            )
            notices.append(notice)
            
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            continue
    
    return notices


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Serve index.html"""
    index_file = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "OK"}


@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve static files"""
    if path.startswith("static/"):
        fpath = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(fpath):
            return FileResponse(fpath)
    
    index_file = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    raise HTTPException(status_code=404)


@app.get("/health")
async def health():
    """Health check"""
    try:
        data = await search_ted_api("*", 1, 1)
        return {"status": "healthy", "api": "ok"}
    except:
        return {"status": "degraded", "api": "error"}


@app.post("/search")
async def search(req: SearchRequest):
    """
    Search endpoint
    FIX 3: Accept { query, page, limit } format from frontend
    FIX 4: Return { total, results } format
    """
    logger.info(f"POST /search")
    
    try:
        ted_response = await search_ted_api(req.query, req.page, req.limit)
        notices = parse_notices(ted_response)
        
        return SearchResponse(
            total=ted_response.get("total", 0),
            results=notices
        )
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 TED Scraper Backend - FIXED")
    print("="*60 + "\n")
    
    uvicorn.run("app:app", host="0.0.0.0", port=8846, reload=False)
