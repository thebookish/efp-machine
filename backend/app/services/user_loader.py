import pandas as pd
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User

USERS_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "users.csv")


async def load_users_from_csv(session: AsyncSession):
    """Load users.csv into the database (upsert)."""
    try:
        df = pd.read_csv(USERS_CSV_PATH)
    except Exception as e:
        print(f"⚠️ Failed to load users.csv: {e}")
        return

    expected = {
        "shortName","userName","alias","tpPostingID","tpUserUID","tpDdeskUID",
        "legalEntity","legalEntityshortName","role","uuid","firmId"
    }
    missing = expected - set(df.columns)
    if missing:
        print(f"⚠️ users.csv missing columns: {missing}")
        return

    for rec in df.to_dict(orient="records"):
        uuid_val = str(rec.get("uuid"))
        if not uuid_val:
            continue

        existing = await session.execute(select(User).where(User.uuid == uuid_val))
        row = existing.scalar_one_or_none()
        if row:
            for k in expected:
                setattr(row, k, str(rec.get(k)) if pd.notna(rec.get(k)) else None)
        else:
            user = User(
                **{k: str(rec.get(k)) if pd.notna(rec.get(k)) else None for k in expected}
            )
            session.add(user)

    await session.commit()
    print(f"✅ Loaded {len(df)} users into DB from users.csv")
