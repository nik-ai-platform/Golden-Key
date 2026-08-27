from apscheduler.schedulers.background import (
    BackgroundScheduler,
)

from app.tasks.daily_job import DailyJob

scheduler = BackgroundScheduler()

daily_job = DailyJob()


def start_scheduler(db):

    scheduler.add_job(
        lambda: daily_job.execute(db),
        trigger="cron",
        hour=5,
        minute=0,
    )

    scheduler.start()