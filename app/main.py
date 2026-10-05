from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Initialize FastAPI application
app = FastAPI(
    title="FlowScore B2B SaaS",
    description='Thin-File Open Banking Credit Underwriter powered by LangGraph',
    version="1.0.0",
)

# Set up Cross-Origin Resource Sharing (CORS) strictly for Production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dashboard.flowscore.ai", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)

import uuid
import logging
from fastapi import Request
logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_trace_id_and_log(request: Request, call_next):
    """Simulates OpenTelemetry Trace ID propagation for observability."""
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    logger.info(f"Trace[{trace_id}] - Request Started: {request.method} {request.url.path}")
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    logger.info(f"Trace[{trace_id}] - Request Completed: Status {response.status_code}")
    return response

@app.get("/", tags=["Health"])
def root():
    return {"message": "Welcome to the FlowScore API"}

@app.get("/health", tags=["Health"])
def health_check():
    """
    Liveness probe for Google Cloud Run / Kubernetes.
    Returns 200 OK if the application is running.
    """
    return {"status": "ok", "service": "FlowScore API"}

from app.api.v1.router import api_router

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
