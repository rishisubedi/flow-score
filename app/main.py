from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
import app.db.models  # Crucial: Import models so Base metadata is populated

# Auto-create tables for local MVP runs (production uses Alembic)
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="FlowScore API",
    description='Thin-File Open Banking Credit Underwriter powered by LangGraph',
    version="0.1.0",
)

# Set up Cross-Origin Resource Sharing (CORS)
# Allows B2B clients (e.g., a frontend dashboard or another backend) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
def root():
    return {"message": "Welcome to the FlowScore API"}

@app.get("/health", tags=["Health"])
def health_check():
    """
    Liveness probe for Google Cloud Run.
    Returns 200 OK if the application is running.
    """
    return {"status": "ok", "service": "FlowScore API"}

from app.api.v1.router import api_router

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
