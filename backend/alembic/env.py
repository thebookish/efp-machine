def to_sync_url(url_str: str) -> str:
    u = make_url(url_str)
    if u.drivername.startswith("sqlite"):
        u = u.set(drivername="sqlite")  # drop +aiosqlite
    elif u.drivername.startswith("postgresql"):
        u = u.set(drivername="postgresql+psycopg2")
    return str(u)
