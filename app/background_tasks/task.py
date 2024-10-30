from app.resources import scheduler


def get_scheduled_jobs():
    return scheduler.get_jobs()
