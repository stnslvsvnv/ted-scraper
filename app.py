"""
TED Scraper Backend - ПРОСТОЙ И РАБОЧИЙ
Tested with TED API directly
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tedapi")

# ============================================================================
# MODELS
# ============================================================================

class SearchRequest(BaseModel):
    query: str = "*"
    page: int = 1
    limit: int = 10


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

# Static files
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

async def search_ted_api(query: str = "*", page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """
    Direct call to TED API v3.0
    
    Based on official TED API documentation:
    - Endpoint: https://api.ted.europa.eu/v3/notices/search
    - Method: POST
    - Required fields: query, fields (must not be empty!)
    """
    
    logger.info(f"🔍 Searching TED API: query='{query}', page={page}, limit={limit}")
    
    # Fields are REQUIRED by TED API!
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
        "query": query,
        "page": page,
        "limit": limit,
        "scope": "ACTIVE",
        "fields": fields
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            logger.info(f"📤 POST to https://api.ted.europa.eu/v3/notices/search")
            
            response = await client.post(
                "https://api.ted.europa.eu/v3/notices/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"📥 Status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"❌ API Error: {error_text}")
                raise Exception(f"TED API returned {response.status_code}: {error_text}")
            
            data = response.json()
            logger.info(f"✓ Got {len(data.get('results', []))} results out of {data.get('total', 0)} total")
            
            return data
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise


def parse_notices(ted_response: Dict[str, Any]) -> List[Notice]:
    """Parse TED API response to Notice objects"""
    notices = []
    
    for item in ted_response.get("results", []):
        try:
            notice = Notice(
                publication_number=item.get("publication-number", "N/A"),
                publication_date=item.get("publication-date"),
                title=item.get("notice-title"),
                buyer=item.get("buyer-name"),
                country=item.get("place-of-performance")
            )
            notices.append(notice)
        except:
            pass
    
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
    
    # Default to index.html
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
    """Search endpoint"""
    logger.info(f"POST /search: query={req.query}")
    
    try:
        ted_response = await search_ted_api(req.query, req.page, req.limit)
        notices = parse_notices(ted_response)
        
        return SearchResponse(
            total=ted_response.get("total", 0),
            results=notices
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 TED Scraper Backend")
    print("="*60)
    print("API: http://localhost:8846/search")
    print("Docs: http://localhost:8846/docs")
    print("="*60 + "\n")
    
    uvicorn.run("app:app", host="0.0.0.0", port=8846, reload=False)
