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
