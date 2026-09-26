from fastapi import APIRouter
from app.api.v1.endpoints import underwrite, admin

api_router = APIRouter()

# Register the underwriting endpoint
api_router.include_router(underwrite.router, prefix="/underwrite", tags=["Underwriting"])
api_router.include_router(admin.router, prefix="/admin/client", tags=["Admin"])
