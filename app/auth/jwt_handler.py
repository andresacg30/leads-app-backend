import time
import jwt
import uuid

from typing import Dict

from settings import Settings


settings = Settings()


def token_response(access_token: str, refresh_token: str) -> Dict[str, str]:
    return {"access_token": access_token, "refresh_token": refresh_token}


secret_key = settings.jwt_secret_key


def sign_jwt(user_id: str, permissions: Dict[str, str]) -> Dict[str, str]:
    access_token_payload = {
        "user_id": user_id,
        "permissions": permissions,
        "expires": time.time() + 2400
    }
    access_token = jwt.encode(access_token_payload, secret_key, algorithm="HS256")

    refresh_token_payload = {
        "user_id": user_id,
        "jti": str(uuid.uuid4()),
        "expires": time.time() + 7200 * 24 * 7
    }
    refresh_token = jwt.encode(refresh_token_payload, secret_key, algorithm="HS256")

    return token_response(access_token, refresh_token)


def sign_impersonate_jwt(user_id: str, permissions: Dict[str, str]) -> Dict[str, str]:
    access_token_payload = {
        "user_id": user_id,
        "permissions": permissions,
        "expires": time.time() + 86400
    }
    access_token = jwt.encode(access_token_payload, secret_key, algorithm="HS256")

    refresh_token_payload = {
        "user_id": user_id,
        "jti": str(uuid.uuid4()),
        "expires": time.time() + 7200 * 24 * 7
    }
    refresh_token = jwt.encode(refresh_token_payload, secret_key, algorithm="HS256")

    return token_response(access_token, refresh_token)


def decode_jwt(token: str) -> dict:
    decoded_token = jwt.decode(token.encode(), secret_key, algorithms=["HS256"])
    return decoded_token if decoded_token["expires"] >= time.time() else {}


def create_access_token(user_id: str, permissions: Dict[str, str]) -> str:
    access_token_payload = {
        "user_id": user_id,
        "permissions": permissions,
        "expires": time.time() + 2400
    }
    access_token = jwt.encode(access_token_payload, secret_key, algorithm="HS256")
    return access_token
