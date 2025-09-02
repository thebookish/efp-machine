# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.deps import engine
from app.routers import efp, ai, health
from app.services.scheduler import setup_scheduler
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
async def on_startup():
    # Auto-create tables if using SQLite (dev only)
    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Setup scheduler tasks
    def on_predict(tag: str):
        print(f"[{now_uk()}] Predict run at {tag}")

    def on_0830_prompt(tag: str):
        print(f"[{now_uk()}] Prompt at {tag}")

    def on_clock_tick(now):
        print(f"[{now}] Tick...")

    setup_scheduler(on_predict, on_0830_prompt, on_clock_tick)
