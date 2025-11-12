"""
TED Scraper Backend - WORKING VERSION
Using ONLY supported field names from TED API error message
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
    Call TED API v3.0
    
    Using SUPPORTED fields from TED API error message:
    - BT-13(t)-Part
    - BT-02-Procedure (title)
    - BT-04-Procedure-Buyer (buyer name)
    - BT-271-Procedure (publication date)
    - organisation-name (buyer)
    - etc.
    """
    
    logger.info(f"🔍 Searching TED API: query='{query}', page={page}, limit={limit}")
    
    # SUPPORTED fields extracted from API error message
    fields = [
        "BT-02-Procedure",                      # Title
        "BT-04-Procedure-Buyer",                # Buyer
        "BT-271-Procedure",                     # Publication date
        "BT-13(t)-Part",                        # Technical identifier
        "organisation-name",                    # Organisation name
        "buyer-name",                           # Buyer name
        "notice-title",                         # Notice title
        "publication-date",                     # Publication date
        "publication-number"                    # Publication number
    ]
    
    payload = {
        "query": query,
        "page": page,
        "limit": limit,
        "scope": "ACTIVE",
        "fields": fields
    }
    
    logger.info(f"Using {len(fields)} fields")
    
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
                error_text = response.text[:1000]
                logger.error(f"❌ API Error: {error_text}")
                raise Exception(f"TED API returned {response.status_code}")
            
            data = response.json()
            
            # Log returned fields
            if data.get("results") and len(data["results"]) > 0:
                sample = data["results"][0]
                logger.info(f"Sample result keys: {list(sample.keys())[:10]}")
            
            logger.info(f"✓ Got {len(data.get('results', []))} results out of {data.get('total', 0)} total")
            
            return data
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise


def parse_notices(ted_response: Dict[str, Any]) -> List[Notice]:
    """Parse TED API response"""
    notices = []
    
    for item in ted_response.get("results", []):
        try:
            # Extract fields (try multiple possible field names)
            pub_num = (
                item.get("publication-number") or 
                item.get("ND-Root") or
                "N/A"
            )
            
            title = (
                item.get("notice-title") or
                item.get("BT-02-Procedure") or
                item.get("title") or
                None
            )
            
            buyer = (
                item.get("buyer-name") or
                item.get("organisation-name") or
                item.get("BT-04-Procedure-Buyer") or
                None
            )
            
            pub_date = (
                item.get("publication-date") or
                item.get("BT-271-Procedure") or
                None
            )
            
            country = (
                item.get("place-of-performance") or
                item.get("country") or
                None
            )
            
            notice = Notice(
                publication_number=str(pub_num),
                publication_date=pub_date,
                title=title,
                buyer=buyer,
                country=country
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
    print("🚀 TED Scraper Backend - SUPPORTED FIELDS")
    print("="*60)
    print("API: http://localhost:8846/search")
    print("Docs: http://localhost:8846/docs")
    print("="*60 + "\n")
    
    uvicorn.run("app:app", host="0.0.0.0", port=8846, reload=False)
