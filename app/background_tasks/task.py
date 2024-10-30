from app.resources import scheduler


def get_scheduled_jobs():
    jobs = scheduler.get_jobs()
    jobs_dict = [job for job in jobs]
    return jobs_dict
