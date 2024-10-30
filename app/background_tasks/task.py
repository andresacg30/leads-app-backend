from app.resources import scheduler


def get_scheduled_jobs():
    if scheduler is None:
        return []
    return list(scheduler.get_jobs())
