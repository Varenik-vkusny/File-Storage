from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from .database import AsyncLocalSession
from .roles import UserRole, FileVisibility
from . import models, security, schemas


async def get_db():
    """
    Зависимость FastAPI для получения сессии базы данных.

    Создает асинхронную сессию для одного запроса и автоматически закрывает ее
    после завершения.
    """

    async with AsyncLocalSession() as session:
        yield session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    access_token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Декодирует JWT токен, находит пользователя в БД и возвращает его.

    Эта зависимость используется для защиты эндпоинтов и получения
    информации о текущем авторизованном пользователе.
    """

    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Вы не авторизованы!",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token=access_token, key=security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        username: str = payload.get("sub")
        if not username:
            raise credential_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credential_exception

    user_result = await db.execute(
        select(models.User).where(models.User.username == token_data.username)
    )
    user_db = user_result.scalar_one_or_none()

    if not user_db:
        raise credential_exception

    return user_db


def require_role(allowed_roles: list[UserRole]):
    """
    Фабрика зависимостей, которая создает "стража", проверяющего роль пользователя.

    Args:
        allowed_roles: Список ролей, которым разрешен доступ.

    Returns:
        Зависимость FastAPI, которая либо возвращает текущего пользователя,
        либо выбрасывает ошибку 403 Forbidden.
    """

    async def check_role(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас недостаточно прав для этого!",
            )
        return current_user

    return check_role


async def get_user_by_id(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Зависимость для получения пользователя по ID из базы данных.

    Выбрасывает ошибку 404 Not Found, если пользователь не найден.
    "Жадно" подгружает связанный отдел.
    """
    user_result = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
        .options(selectinload(models.User.department))
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет пользователя с таким ID!"
        )

    return user


async def get_file_for_user(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.File:
    """
    Зависимость для получения файла по ID с проверкой прав доступа на ЧТЕНИЕ.

    Реализует сложную логику из ТЗ:
    - Админ видит все.
    - Владелец видит свои файлы.
    - Все видят публичные файлы.
    - Менеджер видит все файлы отделов.
    - Пользователь видит файлы своего отдела.
    """

    file_res = await db.execute(
        select(models.File)
        .options(selectinload(models.File.owner))
        .where(models.File.id == file_id)
    )
    file = file_res.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет файла с таким ID"
        )

    if current_user.role == UserRole.ADMIN:
        return file
    if file.owner_id == current_user.id:
        return file
    if file.visibility == FileVisibility.PUBLIC:
        return file
    if file.visibility == FileVisibility.DEPARTMENT:
        if current_user.role == UserRole.MANAGER:
            return file
        if current_user.department_id == file.department_id:
            return file

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет доступа к этому файлу!"
    )


async def get_file_to_delete(
    file_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> models.File:
    """
    Зависимость для получения файла по ID с проверкой прав доступа на УДАЛЕНИЕ.

    Реализует логику из ТЗ:
    - Админ может удалить любой файл.
    - Менеджер может удалить файл из своего отдела.
    - Пользователь может удалить только свой файл.
    """

    file = await db.get(models.File, file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден!"
        )

    if current_user.role == UserRole.ADMIN:
        return file
    if current_user.role == UserRole.MANAGER:
        if current_user.department_id == file.department_id:
            return file
    if current_user.role == UserRole.USER:
        if current_user.id == file.owner_id:
            return file

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="У вас недостаточно прав для удаления этого файла!",
    )
