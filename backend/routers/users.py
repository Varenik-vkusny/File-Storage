from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .. import schemas, models, security
from ..dependencies import get_db, require_role, get_user_by_id
from ..roles import UserRole


router = APIRouter()


@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: schemas.UserIn,
    db: AsyncSession = Depends(get_db),
    current_admin_or_manager: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """
    Создает нового пользователя в системе.

    Доступно только для пользователей с ролями 'ADMIN' и 'MANAGER'.
    """

    user_result = await db.execute(
        select(models.User).where(models.User.username == user_data.username)
    )
    user_db = user_result.scalar_one_or_none()

    if user_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким именем уже есть!",
        )

    new_user = models.User(
        username=user_data.username,
        password_hash=security.hash_password(user_data.password),
        department_id=user_data.department_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.department))
        .where(models.User.id == new_user.id)
    )
    return result.scalar_one()


@router.get(
    "/{user_id}", response_model=schemas.UserOut, status_code=status.HTTP_200_OK
)
async def get_user_info(
    user: models.User = Depends(get_user_by_id),
    current_admin_or_manager: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """
    Возвращает информацию о пользователе по его ID.

    Доступно только для пользователей с ролями 'ADMIN' и 'MANAGER'.
    """

    return user


@router.put(
    "/{user_id}/role", response_model=schemas.UserOut, status_code=status.HTTP_200_OK
)
async def change_user_role(
    new_data: schemas.UserRoleUpdate,
    user: models.User = Depends(get_user_by_id),
    current_admin_or_manager: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Изменяет роль пользователя.

    Доступно только для пользователей с ролями 'ADMIN' и 'MANAGER'.
    """

    user.role = new_data.role
    db.add(user)
    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.department))
        .where(models.User.id == user.id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[schemas.UserOut], status_code=status.HTTP_200_OK)
async def get_users_by_department(
    department_id: int,
    current_admin_or_manager: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список пользователей указанного отдела.

    Доступно только для пользователей с ролями 'ADMIN' и 'MANAGER'.
    """

    users_result = await db.execute(
        select(models.User)
        .where(models.User.department_id == department_id)
        .options(selectinload(models.User.department))
    )
    users = users_result.scalars().all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователей в этом отделе не найдено!",
        )

    return users
