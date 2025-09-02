# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.deps import engine
from app.routers import efp, ai, health
from app.services.scheduler import start_scheduler
from app.utils.time import now_uk
from app.models import Base
import asyncio

app = FastAPI(title="EFP Machine API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.ALLOW_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(efp.router)
app.include_router(ai.router)


@app.on_event("startup")
async def startup_event():
    start_scheduler()
