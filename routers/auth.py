from schemas.user import PasswordChange
from fastapi import APIRouter, Body, Depends, status, Request, Response, HTTPException
from typing import Annotated
from db_models.user import User
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserOut
from schemas.token import AccessToken
from core.database import get_db
from core.cookies import set_refresh_cookie, clear_refresh_cookie, REFRESH_COOKIE_NAME
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordRequestForm
from dependancies import get_current_user, oauth2_scheme
from services.auth_service import AuthService

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut)
@limiter.limit(
    "5/minute"
)  # Max 5 registrations per minute(slowapi Track rate limits per IP address from request obj(request obj is auth injected by fast api every request))
async def register_user(
    request: Request, user: Annotated[UserCreate, Body()], db: Session = Depends(get_db)
):
    return AuthService.register_user(db=db, user_data=user)


@router.post("/login", response_model=AccessToken)
@limiter.limit("10/minute")
async def login_user(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    result = AuthService.authenticate_user(
        db=db, email=form_data.username, password=form_data.password
    )
    set_refresh_cookie(response, result["refresh_token"])
    return {"access_token": result["access_token"], "token_type": result["token_type"]}


@router.post("/refresh", response_model=AccessToken)
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )
    result = AuthService.refresh_tokens(db=db, refresh_token=refresh_token)
    set_refresh_cookie(response, result["refresh_token"])
    return {"access_token": result["access_token"], "token_type": result["token_type"]}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def logout_user(
    request: Request,
    response: Response,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await AuthService.logout_user(db=db, access_token=token)
    clear_refresh_cookie(response)
    return None


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    response: Response,
    passwords: Annotated[PasswordChange, Body()],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AuthService.change_user_password(
        db=db,
        user=current_user,
        old_password=passwords.old_password,
        new_password=passwords.new_password,
    )
    clear_refresh_cookie(response)
    return result
