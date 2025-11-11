"""
TED Scraper - Combined Frontend + Backend Application
Ports: 8846 (Frontend), 8847 (Backend API)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

TED_API_BASE_URL = "https://ted.europa.eu/api/v3.0/notices/search"
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
    return_fields: Optional[List[str]] = Field(["CONTENT"])


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

# Mount static files - create empty directory if needed
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
        query_parts.append(f"FT={filters.full_text}")
    
    if filters.cpv_codes:
        cpv_query = " OR ".join([f"classification-cpv = {code}" for code in filters.cpv_codes])
        query_parts.append(f"({cpv_query})" if len(filters.cpv_codes) > 1 else cpv_query)
    
    if filters.buyer_countries:
        country_query = " OR ".join([f"buyer-country = {country}" for country in filters.buyer_countries])
        query_parts.append(f"({country_query})" if len(filters.buyer_countries) > 1 else country_query)
    
    if filters.notice_types:
        notice_query = " OR ".join([f"notice-type = {notice_type}" for notice_type in filters.notice_types])
        query_parts.append(f"({notice_query})" if len(filters.notice_types) > 1 else notice_query)
    
    if filters.publication_date_from:
        query_parts.append(f"publication-date >= {filters.publication_date_from}")
    
    if filters.publication_date_to:
        query_parts.append(f"publication-date <= {filters.publication_date_to}")
    
    if filters.min_value:
        query_parts.append(f"contract-estimated-value >= {filters.min_value}")
    
    if filters.max_value:
        query_parts.append(f"contract-estimated-value <= {filters.max_value}")
    
    if filters.procedure_type:
        query_parts.append(f"procedure-type = {filters.procedure_type}")
    
    if filters.contract_status:
        query_parts.append(f"contract-status = {filters.contract_status}")
    
    if not query_parts:
        query_parts.append("*")
    
    query = " AND ".join(query_parts)
    logger.info(f"Built TED Query: {query}")
    return query


def parse_ted_response(data: Dict[str, Any]) -> List[NoticeItem]:
    """Parse TED API response to NoticeItem objects"""
    notices = []
    
    for notice in data.get("notices", []):
        try:
            publication_number = notice.get("ND", {}).get("value", "N/A")
            
            notice_item = NoticeItem(
                publication_number=publication_number,
                publication_date=notice.get("PD", {}).get("value"),
                notice_type=notice.get("BT-02-notice", {}).get("value"),
                buyer_name=notice.get("CA", {}).get("value"),
                title=notice.get("TI", {}).get("value"),
                cpv_codes=notice.get("CPV", {}).get("value", []) if isinstance(notice.get("CPV", {}).get("value"), list) else None,
                country=notice.get("CY", {}).get("value"),
                estimated_value=notice.get("OC", {}).get("value"),
                content_html=notice.get("CONTENT", {}).get("value"),
                url=f"https://ted.europa.eu/en/notice/{publication_number}",
                metadata={"raw_data": notice}
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
    """Call TED Search API"""
    
    if fields is None:
        fields = ["CONTENT"]
    
    request_body = {
        "q": query,
        "fields": fields,
        "page": page,
        "pageSize": page_size,
        "scope": scope,
        "paginationMode": "page_number_mode"
    }
    
    logger.info(f"Calling TED API with query: {query[:100]}...")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                TED_API_BASE_URL,
                json=request_body,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"Got {len(data.get('notices', []))} results from TED API")
            
            return data
            
    except httpx.HTTPError as e:
        logger.error(f"TED API error: {e}")
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
    
    logger.info(f"Search request: {request.filters}")
    
    # Build query
    query = build_ted_query(request.filters)
    
    # Call TED API
    ted_response = await call_ted_api(
        query=query,
        page=request.page,
        page_size=request.page_size,
        scope=request.scope.value,
        fields=request.return_fields or ["CONTENT"]
    )
    
    # Parse response
    notices = parse_ted_response(ted_response)
    
    # Calculate pages
    total_notices = ted_response.get("totalNotices", 0)
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
    
    query = f"publication-number = {notice_id}"
    
    ted_response = await call_ted_api(
        query=query,
        page=1,
        page_size=1,
        fields=["CONTENT"]
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
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8846,
        reload=False,
        log_level="info"
    )
