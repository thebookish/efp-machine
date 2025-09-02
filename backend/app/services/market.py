# backend/app/services/market.py
import json
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def fetch_cash_level(index: str) -> float | None:
    q = f"Provide latest cash index level for {index}, number only."
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": q}],
    )
    try:
        return float(resp.choices[0].message.content.strip())
    except Exception:
        return None

async def fetch_rates() -> dict:
    q = "Give me current SONIA and Euribor 3M rates as plain numbers in JSON: {\"SONIA\":x, \"EURIBOR_3M\":y}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": q}],
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {"SONIA": None, "EURIBOR_3M": None}

async def fetch_dividends(index: str) -> str:
    q = f"Upcoming dividend events for {index}, return concise string."
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": q}],
    )
    return resp.choices[0].message.content.strip()


latest_rates = {"SONIA": None, "EURIBOR_3M": None}

async def fetch_rates() -> dict:
    """
    Fetch SONIA and Euribor 3M using OpenAI.
    Falls back to the last known values if parsing fails.
    """
    q = (
        "Give me current SONIA and Euribor 3M rates as plain JSON, "
        "format: {\"SONIA\": number, \"EURIBOR_3M\": number}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": q}],
            temperature=0,
        )
        parsed = json.loads(resp.choices[0].message.content)
        latest_rates.update(parsed)
        return parsed
    except Exception as e:
        print("fetch_rates error:", e)
        return latest_rates
    
latest_market_values: dict[str, float | None] = {
    "SX5E": None,
    "SX7E": None,
    "DAX": None,
    "FTSE": None,
    "CAC": None,
}

async def fetch_market_values() -> dict:
    """
    Fetch approximate live market values for common indices using OpenAI.
    Falls back to cached values if parsing fails.
    """
    q = (
        "Provide latest index levels for SX5E, SX7E, DAX, FTSE, CAC as JSON only. "
        "Format: {\"SX5E\":4212.5, \"SX7E\":3150.2, \"DAX\":18250.0, \"FTSE\":7400.0, \"CAC\":7425.0}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": q}],
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = json.loads(raw)
        # Ensure only expected keys
        for k in latest_market_values.keys():
            if k in parsed:
                latest_market_values[k] = parsed[k]
        return latest_market_values
    except Exception as e:
        print("fetch_market_values error:", e)
        return latest_market_values