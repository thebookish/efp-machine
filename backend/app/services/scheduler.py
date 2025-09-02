from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.utils.time import now_uk

def setup_scheduler(on_predict, on_0830_prompt, on_clock_tick):
    sched = AsyncIOScheduler(timezone='Europe/London')
    sched.add_job(lambda: on_clock_tick(now_uk()), 'cron', minute='*', id='clock-tick')
    sched.add_job(lambda: on_predict('07:50'), 'cron', hour=7, minute=50, id='predict-0750')
    sched.add_job(lambda: on_0830_prompt('08:30'), 'cron', hour=8, minute=30, id='prompt-0830')
    return sched
