"""
TED Scraper - Combined Frontend + Backend Application
Ports: 8846 (Frontend), 8847 (Backend API)
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
# Конфигурация
# ============================================================================

TED_API_BASE_URL = "https://api.ted.europa.eu/v3/notices/search"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

# Создаем папку static если её нет
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory: {static_dir}")

# ============================================================================
# Enums
# ============================================================================

class ScopeEnum(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SENSITIVE = "SENSITIVE"
    ALL = "ALL_DATA"


class SortColumnEnum(str, Enum):
    PUBLICATION_NUMBER = "publication-number"
    PUBLICATION_DATE = "publication-date"
    NOTICE_TYPE = "notice-type"
    BUYER_NAME = "buyer-name"


class SortOrderEnum(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class PaginationModeEnum(str, Enum):
    PAGE_NUMBER = "page_number_mode"
    ITERATION = "iteration_mode"


# ============================================================================
# Pydantic Models
# ============================================================================

class SearchFilters(BaseModel):
    full_text: Optional[str] = None
    cpv_codes: Optional[List[str]] = None
    buyer_countries: Optional[List[str]] = None
    notice_types: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    publication_date_from: Optional[date] = None
    publication_date_to: Optional[date] = None
    procedure_type: Optional[str] = None
    contract_status: Optional[str] = None


class SearchRequest(BaseModel):
    filters: SearchFilters = Field(...)
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    scope: ScopeEnum = Field(ScopeEnum.ACTIVE)
    sort_column: Optional[SortColumnEnum] = Field(SortColumnEnum.PUBLICATION_NUMBER)
    sort_order: Optional[SortOrderEnum] = Field(SortOrderEnum.DESC)
    pagination_mode: PaginationModeEnum = Field(PaginationModeEnum.PAGE_NUMBER)
    return_fields: Optional[List[str]] = Field(["publication-number", "notice-title", "buyer-name"])


class NoticeItem(BaseModel):
    publication_number: str
    publication_date: Optional[str] = None
    notice_type: Optional[str] = None
    buyer_name: Optional[str] = None
    title: Optional[str] = None
    cpv_codes: Optional[List[str]] = None
    country: Optional[str] = None
    estimated_value: Optional[float] = None
    deadline: Optional[str] = None
    content_html: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    total_notices: int
    total_pages: int
    current_page: int
    page_size: int
    notices: List[NoticeItem]
    search_query: str
    timestamp: datetime


class HealthResponse(BaseModel):
    status: str
    ted_api_available: bool
    timestamp: datetime


class ProcessingTask(BaseModel):
    task_id: str
    task_type: str
    notice_ids: List[str]
    parameters: Optional[Dict[str, Any]] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="TED Scraper - Combined",
    description="Frontend + Backend for TED European Tenders Search",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists(static_dir):
    try:
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Mounted static files from: {static_dir}")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")

# Global state
processing_tasks: Dict[str, ProcessingTask] = {}

# ============================================================================
# Helper Functions
# ============================================================================

def build_ted_query(filters: SearchFilters) -> str:
    """Build TED API Expert Query from filters"""
    query_parts = []
    
    if filters.full_text:
        query_parts.append(filters.full_text)
    
    if filters.cpv_codes:
        cpv_query = " OR ".join([f"({code})" for code in filters.cpv_codes])
        query_parts.append(f"cpv-code:{cpv_query}")
    
    if filters.buyer_countries:
        country_query = " OR ".join([f"({country})" for country in filters.buyer_countries])
        query_parts.append(f"place-of-performance:{country_query}")
    
    if filters.publication_date_from:
        query_parts.append(f"publication-date:[{filters.publication_date_from}]")
    
    if filters.publication_date_to:
        query_parts.append(f"publication-date:[*+TO+{filters.publication_date_to}]")
    
    if not query_parts:
        # Если никаких фильтров - используем простой запрос
        query_parts.append("*")
    
    query = " AND ".join(query_parts)
    logger.info(f"Built TED Query: {query}")
    return query


def parse_ted_response(data: Dict[str, Any]) -> List[NoticeItem]:
    """Parse TED API response to NoticeItem objects"""
    notices = []
    
    # Новый API возвращает результаты в массиве "results"
    results = data.get("results", [])
    
    for notice in results:
        try:
            publication_number = notice.get("publication-number", "N/A")
            
            # Получаем значения, обрабатывая разные форматы данных
            title = notice.get("notice-title") or notice.get("notice-title", {}).get("value", "N/A")
            buyer = notice.get("buyer-name") or notice.get("buyer-name", {}).get("value", "N/A")
            country = notice.get("place-of-performance") or notice.get("place-of-performance", {}).get("value", "N/A")
            
            # CPV коды могут быть строкой или списком
            cpv = notice.get("cpv-code", [])
            if isinstance(cpv, str):
                cpv = [cpv]
            elif not isinstance(cpv, list):
                cpv = []
            
            notice_item = NoticeItem(
                publication_number=publication_number,
                publication_date=notice.get("publication-date"),
                notice_type=notice.get("notice-type"),
                buyer_name=buyer,
                title=title,
                cpv_codes=cpv if cpv else None,
                country=country,
                url=f"https://ted.europa.eu/en/notice/{publication_number}" if publication_number != "N/A" else None,
            )
            
            notices.append(notice_item)
            
        except Exception as e:
            logger.warning(f"Error parsing notice: {e}")
            continue
    
    return notices


async def call_ted_api(
    query: str,
    page: int = 1,
    page_size: int = 10,
    scope: str = "ACTIVE",
    fields: List[str] = None
) -> Dict[str, Any]:
    """Call TED Search API v3 - usando URL query parameters (NO JSON body)"""
    
    if fields is None:
        fields = ["publication-number", "notice-title", "buyer-name", "publication-date", "notice-type", "cpv-code", "place-of-performance"]
    
    # ВАЖНО: TED API v3 требует query parameters в URL, не JSON body!
    params = {
        "query": query,  # ← Query string
        "fields": ",".join(fields),  # ← Comma-separated fields
        "page": page,
        "limit": page_size,
        "scope": scope,
    }
    
    logger.info(f"Calling TED API v3 with query: {query[:100]}...")
    logger.info(f"Endpoint: {TED_API_BASE_URL}")
    logger.debug(f"Query parameters: {params}")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # МЕТОД: GET с query parameters (не POST с JSON body)
            response = await client.get(
                TED_API_BASE_URL,
                params=params,
                headers={"Accept": "application/json"}
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            total_results = data.get("total", 0)
            results_count = len(data.get("results", []))
            logger.info(f"Got {results_count} results from {total_results} total matches")
            
            return data
            
    except httpx.HTTPError as e:
        logger.error(f"TED API HTTP error: {e}")
        logger.error(f"Response text: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        raise HTTPException(status_code=502, detail=f"TED API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


# ============================================================================
# Frontend Routes
# ============================================================================

@app.get("/")
async def root():
    """Serve index.html"""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not found", "message": "index.html not loaded"}


@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve static files"""
    if path.startswith("static/"):
        file_path = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    # Fallback to index for SPA
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    raise HTTPException(status_code=404, detail="Not found")


# ============================================================================
# API Routes
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health"""
    
    ted_available = False
    
    try:
        await call_ted_api(query="*", page=1, page_size=1)
        ted_available = True
    except Exception as e:
        logger.warning(f"TED API not available: {e}")
    
    return HealthResponse(
        status="healthy" if ted_available else "degraded",
        ted_api_available=ted_available,
        timestamp=datetime.now()
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for tenders"""
    
    logger.info(f"Search request received")
    
    # Build query
    query = build_ted_query(request.filters)
    
    # Call TED API
    ted_response = await call_ted_api(
        query=query,
        page=request.page,
        page_size=request.page_size,
        scope=request.scope.value,
        fields=request.return_fields
    )
    
    # Parse response
    notices = parse_ted_response(ted_response)
    
    # Calculate pages
    total_notices = ted_response.get("total", 0)
    total_pages = (total_notices + request.page_size - 1) // request.page_size
    
    return SearchResponse(
        total_notices=total_notices,
        total_pages=total_pages,
        current_page=request.page,
        page_size=request.page_size,
        notices=notices,
        search_query=query,
        timestamp=datetime.now()
    )


@app.post("/process", status_code=202)
async def create_processing_task(task: ProcessingTask, background_tasks: BackgroundTasks):
    """Create a processing task for microservices"""
    
    logger.info(f"Processing task created: {task.task_id}")
    processing_tasks[task.task_id] = task
    
    return {
        "task_id": task.task_id,
        "status": "accepted",
        "message": "Task accepted"
    }


@app.get("/process/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = processing_tasks[task_id]
    
    return {
        "task_id": task_id,
        "status": task.status,
        "created_at": task.created_at,
        "task_type": task.task_type
    }


@app.get("/notice/{notice_id}")
async def get_notice_details(notice_id: str):
    """Get full notice details"""
    
    query = f"publication-number:{notice_id}"
    
    ted_response = await call_ted_api(
        query=query,
        page=1,
        page_size=1,
        fields=["publication-number", "notice-title", "buyer-name", "publication-date", "notice-type", "cpv-code", "place-of-performance"]
    )
    
    notices = parse_ted_response(ted_response)
    
    if not notices:
        raise HTTPException(status_code=404, detail=f"Notice {notice_id} not found")
    
    return notices[0]


@app.get("/statistics")
async def get_statistics():
    """Get processing statistics"""
    
    total_tasks = len(processing_tasks)
    completed = sum(1 for t in processing_tasks.values() if t.status == "completed")
    failed = sum(1 for t in processing_tasks.values() if t.status == "failed")
    pending = sum(1 for t in processing_tasks.values() if t.status == "pending")
    
    return {
        "total_tasks": total_tasks,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "success_rate": (completed / total_tasks * 100) if total_tasks > 0 else 0
    }


# ============================================================================
# Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 TED Scraper - Combined Frontend + Backend")
    print("="*60)
    print("📖 Frontend: http://localhost:8846")
    print("🔌 API: http://localhost:8846/search")
    print("📚 API Docs: http://localhost:8846/api/docs")
    print("💚 Health: http://localhost:8846/health")
    print("🌐 TED API: https://api.ted.europa.eu/v3/notices/search")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8846,
        reload=False,
        log_level="info"
    )
