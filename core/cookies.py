from fastapi import Response

from core.config import get_settings

settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
