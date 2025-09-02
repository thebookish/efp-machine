from datetime import datetime
import pytz
from app.config import settings

TZ = pytz.timezone(settings.TIMEZONE_UK)

def now_uk() -> datetime:
    return datetime.now(TZ)

def is_0750() -> bool:
    t = now_uk()
    return t.hour == 7 and t.minute == 50

def is_0830() -> bool:
    t = now_uk()
    return t.hour == 8 and t.minute == 30
