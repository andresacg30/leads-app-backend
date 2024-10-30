import logging

from fastapi import APIRouter, Depends

from app.background_tasks.task import get_scheduled_jobs
from app.models.user import UserModel
from app.auth.jwt_bearer import get_current_user

router = APIRouter(prefix="/api/task", tags=["task"])

logger = logging.getLogger(__name__)


@router.get("/scheduled-tasks")
async def scheduled_jobs(user: UserModel = Depends(get_current_user)):
    try:
        jobs = get_scheduled_jobs()
        logger.info(f"Scheduled jobs: {jobs}")
        return jobs
    except Exception as e:
        logger.error(f"Error retrieving scheduled jobs: {e}")
        return {"error": str(e)}
