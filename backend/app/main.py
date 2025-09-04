# backend/app/main.py
from app.services.efp_run import fetch_daily_efp_run
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.deps import engine
from app.routers import efp, ai, health, blotter
from app.services.scheduler import start_scheduler
from app.utils.time import now_uk
from app.models import Base
import asyncio

app = FastAPI(title="EFP Machine API", version="0.1.0")
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "https://efp-machine-3.onrender.com",  # your deployed frontend URL
]
# CORS
app.add_middleware(
    CORSMiddleware,
     allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(efp.router)
app.include_router(ai.router)
app.include_router(blotter.router)

@app.get("/")
async def root():
    return {"message": "EFP Machine backend is running"}

@app.on_event("startup")

async def startup_event():
    start_scheduler()
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-generate daily EFP run if DB empty
    await fetch_daily_efp_run()
