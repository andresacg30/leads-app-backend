import logging

from fastapi import APIRouter, Depends

from app.background_tasks.job import get_scheduled_jobs,clear_scheduled_jobs
from app.models.user import UserModel
from app.auth.jwt_bearer import get_current_user

router = APIRouter(prefix="/api/job", tags=["job"])

logger = logging.getLogger(__name__)


@router.get("/scheduled-jobs")
async def scheduled_jobs(user: UserModel = Depends(get_current_user)):
    try:
        jobs = get_scheduled_jobs()
        logger.info(f"Scheduled jobs: {jobs}")
        return jobs
    except Exception as e:
        logger.error(f"Error retrieving scheduled jobs: {e}")
        return {"error": str(e)}


@router.delete("/scheduled-jobs")
async def delete_scheduled_jobs(user: UserModel = Depends(get_current_user)):
    try:
        clear_scheduled_jobs()
        logger.info("Scheduled jobs cleared")
        return {"message": "Scheduled jobs cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing scheduled jobs: {e}")
        return {"error": str(e)}
