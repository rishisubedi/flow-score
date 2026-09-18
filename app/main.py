from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# We will include our underwriting router here in the next sprint days
# app.include_router(underwrite.router, prefix="/v1")
