from fastapi import APIRouter
from app.api.v1.endpoints import underwrite, admin, auth

api_router = APIRouter()

# Register the endpoints
api_router.include_router(underwrite.router, prefix="/underwrite", tags=["Underwriting"])
api_router.include_router(admin.router, prefix="/admin/client", tags=["Admin"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])
