from datetime import date, timedelta

def third_friday(year: int, month: int) -> date:
    d = date(year, month, 15)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d

def classify_expiry(today: date):
    monthly = ['CAC','IBEX','AEX','OMX']
    quarterly = ['SX5E','SX5E CC','FTSE','DAX','SMI','MIB','SX7E','SX7E CC']
    expiry_day = third_friday(today.year, today.month)
    statuses = {}
    for name in monthly + quarterly:
        if today < expiry_day:
            statuses[name] = 'Pending'
        elif today == expiry_day:
            statuses[name] = 'In expiry window'
        else:
            statuses[name] = 'Expired'
    return statuses, expiry_day
