from fastapi import APIRouter, Depends

from app.background_tasks.task import get_scheduled_jobs
from app.models.user import UserModel
from app.auth.jwt_bearer import get_current_user

router = APIRouter(prefix="/api/task", tags=["task"])


@router.get("/scheduled-jobs")
def scheduled_jobs(user: UserModel = Depends(get_current_user)):
    return get_scheduled_jobs()
