import json
from sqlalchemy import delete, func
from datetime import date, datetime
from openai import OpenAI
from app.config import settings
from app.models import EfpRun
from app.deps import AsyncSessionLocal

client = OpenAI(api_key=settings.OPENAI_API_KEY)

FALLBACK_EFP_RUN = [
    {"index_name": "SX5E", "bid": 9.375, "offer": 9.625, "cash_ref": 5481},
    {"index_name": "FTSE", "bid": 22.25, "offer": 23.0, "cash_ref": 9317},
    {"index_name": "DAX", "bid": 41.0, "offer": 44.0, "cash_ref": 24308},
    {"index_name": "SMI", "bid": -10.0, "offer": -8.75, "cash_ref": 12230},
    {"index_name": "MIB", "bid": 69.0, "offer": 73.0, "cash_ref": 43048},
    {"index_name": "CAC", "bid": 13.0, "offer": 14.5, "cash_ref": 7933},
    {"index_name": "IBEX", "bid": 18.5, "offer": 20.0, "cash_ref": 15301},
    {"index_name": "AEX", "bid": 0.9, "offer": 1.05, "cash_ref": 906.2},
    {"index_name": "OMX", "bid": 3.4, "offer": 4.2, "cash_ref": 2649},
    {"index_name": "SX7E", "bid": 0.28, "offer": 0.32, "cash_ref": 235.5},
]
ALLOWED_EFPS = [
    "SX5E", "FTSE", "DAX", "SMI", "MIB",
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC"
]
async def fetch_daily_efp_run():
    prompt = """
    Get today's official European equity index futures EFP run.
    Reply ONLY in JSON array like:
    [{"index_name":"SX5E","bid":9.375,"offer":9.625,"cash_ref":5481}, ...]
     for ONLY these indices (do not include anything else):
    {  "SX5E", "FTSE", "DAX", "SMI", "MIB",
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC"}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a market data retriever."},
                      {"role": "user", "content": prompt}]
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception:
        data = FALLBACK_EFP_RUN

    # Insert into DB
    async with AsyncSessionLocal() as session:
            await session.execute(
                delete(EfpRun).where(func.date(EfpRun.created_at) == date.today())
            )
            await session.commit()

            for row in data:
                efp = EfpRun(
                    index_name=row["index_name"],
                    bid=row["bid"],
                    offer=row["offer"],
                    cash_ref=row["cash_ref"],
                    created_at=datetime.now()
                )
                session.add(efp)

            await session.commit()

    return data
