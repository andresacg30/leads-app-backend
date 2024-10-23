import app.controllers.user as user_controller

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.jwt_handler import decode_jwt
from app.models.user import UserModel

from settings import Settings


settings = Settings()


def verify_jwt(jwtoken: str) -> bool:
    isTokenValid: bool = False

    payload = decode_jwt(jwtoken)
    if payload:
        isTokenValid = True
    return isTokenValid


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        api_key = request.headers.get("x-api-key")
        if api_key and api_key == settings.api_key:
            return api_key
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication token"
                )
            if not verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token"
                )

            return credentials.credentials


async def get_current_user(authorization: str = Depends(JWTBearer())) -> UserModel:
    if authorization == settings.api_key:
        return UserModel(
            email="info@leadconex.com",
            password=settings.api_key,
            name="LeadConex API",
            region="API",
            permissions=["admin"]
        )
    payload = decode_jwt(authorization)
    if not payload:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    try:
        user = await user_controller.get_user_by_field(email=payload.get("user_id"))
    except user_controller.UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return user
