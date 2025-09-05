from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from .database import AsyncLocalSession
from .roles import UserRole
from . import models, security, schemas

async def get_db():
    async with AsyncLocalSession() as session:
        yield session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


async def get_current_user(access_token: str=Depends(oauth2_scheme), db: AsyncSession=Depends(get_db)):

    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Вы не авторизованы!'
    )

    try:
        payload = jwt.decode(token=access_token, key=security.SECRET_KEY, algorithms=[security.ALGORITHM])

        username: str = payload.get('sub')

        if not username: 
            raise credential_exception
        
        token_data = schemas.TokenData(username=username)
        
    except JWTError:
        raise credential_exception
    
    user_result = await db.execute(select(models.User).where(models.User.username == token_data.username))

    user_db = user_result.scalar_one_or_none()

    if not user_db:
        raise credential_exception
    
    return user_db 


def require_role(allowed_roles: list[UserRole]):
    async def check_role(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='У вас недостаточно прав для этого!'
            )
        
        return current_user
    return check_role


async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)) -> models.User:

    user_result = await db.execute((select(models.User).where(models.User.id == user_id)).options(selectinload(models.User.department)))

    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Нет пользователя с таким ID!'
        )
    
    return user