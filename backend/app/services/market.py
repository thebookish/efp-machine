import yfinance as yf

SYMBOL_MAP = {
    "SX5E": "^STOXX50E",   # Euro Stoxx 50
    "DAX": "^GDAXI",       # German DAX
    "FTSE": "^FTSE",       # FTSE 100
    "CAC": "^FCHI",        # CAC 40
    "SMI": "^SSMI",        # Swiss Market Index
    "IBEX": "^IBEX",
    "AEX": "^AEX",
    # Add more as needed
}

async def get_quote(symbol: str) -> dict:
    try:
        yf_symbol = SYMBOL_MAP.get(symbol.upper(), symbol)
        ticker = yf.Ticker(yf_symbol)
        info = ticker.fast_info
        return {
            "symbol": symbol,
            "mapped_symbol": yf_symbol,
            "last_price": info.get("lastPrice"),
            "currency": info.get("currency"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
