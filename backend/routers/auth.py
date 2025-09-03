from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from .. import models, schemas, security
from ..dependencies import get_db


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')


@router.post('/register', response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: schemas.UserIn, db: AsyncSession=Depends(get_db)):

    user_result = await db.execute(select(models.User).where(models.User.username == user_data.username))

    user_db = user_result.scalar_one_or_none()

    if user_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Пользователь с таким именем уже есть!'
        )
    
    new_user = models.User(username=user_data.username, password_hash=security.hash_password(user_data.password))

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post('/auth/login', response_model=schemas.Token, status_code=status.HTTP_200_OK)
async def login(user_data: OAuth2PasswordRequestForm=Depends(), db: AsyncSession=Depends(get_db)):

    user_result = await db.execute(select(models.User).where(models.User.username == user_data.username))

    user_db = user_result.scalar_one_or_none()

    authorization_exception = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Неправильное имя или пароль!'
        )

    if not user_db:
        raise authorization_exception
    
    if not security.verify_password(user_data.password, user_db.password_hash):
        raise authorization_exception
    
    data = {'sub': user_data.username}

    access_token = security.create_access_token(data=data)

    return {
        'access_token': access_token,
        'token_type': 'bearer'
    }


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