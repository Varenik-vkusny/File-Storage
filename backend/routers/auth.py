from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .. import models, schemas, security
from ..dependencies import get_db, get_current_user


router = APIRouter()


@router.post("/login", response_model=schemas.Token, status_code=status.HTTP_200_OK)
async def login(
    user_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Аутентифицирует пользователя и возвращает JWT токен.

    Принимает имя пользователя и пароль в формате x-www-form-urlencoded.
    В случае успеха возвращает access_token.
    """

    user_result = await db.execute(
        select(models.User).where(models.User.username == user_data.username)
    )
    user_db = user_result.scalar_one_or_none()

    authorization_exception = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Неправильное имя или пароль!"
    )

    if not user_db:
        raise authorization_exception

    if not security.verify_password(user_data.password, user_db.password_hash):
        raise authorization_exception

    data = {"sub": user_db.username}
    access_token = security.create_access_token(data=data)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut, status_code=status.HTTP_200_OK)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """
    Возвращает информацию о текущем авторизованном пользователе.

    Требует валидный JWT токен в заголовке Authorization.
    """

    return current_user
