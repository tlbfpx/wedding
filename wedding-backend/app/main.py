from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.utils.errors import AppException, ErrorDetail
from app.api import auth, customers, suppliers, orders, approvals, events, venues, dashboard, users

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error.model_dump()})


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(customers.router, prefix="/api/v1", tags=["customers"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(venues.router, prefix="/api/v1/venues", tags=["venues"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
