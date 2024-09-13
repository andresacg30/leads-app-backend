import time
from typing import Dict

import jwt

from settings import Settings


settings = Settings()


def token_response(token: str):
    return {"access_token": token}


secret_key = settings.jwt_secret_key


def sign_jwt(user_id: str, permissions: Dict[str, str]) -> Dict[str, str]:
    payload = {"user_id": user_id, "permissions": permissions, "expires": time.time() + 2400}
    return token_response(jwt.encode(payload, secret_key, algorithm="HS256"))


def decode_jwt(token: str) -> dict:
    decoded_token = jwt.decode(token.encode(), secret_key, algorithms=["HS256"])
    return decoded_token if decoded_token["expires"] >= time.time() else {}
