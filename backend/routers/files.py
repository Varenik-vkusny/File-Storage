import uuid
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File as FastapiFile,
    HTTPException,
    status,
    Form,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..s3_client import upload_file_to_s3, create_presigned_url, delete_file_from_s3
from ..roles import FileVisibility, UserRole
from ..dependencies import (
    get_db,
    get_current_user,
    get_file_for_user,
    get_file_to_delete,
)
from .. import models, schemas
from ..tasks import extract_metadata
from ..config import get_settings, Settings


router = APIRouter()


ALLOWED_FILE_TYPES_USER = ["application/pdf"]
ALLOWED_MIMETYPES_MANAGER_ADMIN = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
]

MAX_FILE_SIZE_USER = 10 * 1024 * 1024
MAX_FILE_SIZE_MANAGER = 50 * 1024 * 1024
MAX_FILE_SIZE_ADMIN = 100 * 1024 * 1024


@router.post(
    "/upload", response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    file: UploadFile = FastapiFile(...),
    visibility: FileVisibility = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Загружает файл в S3 хранилище и создает запись в базе данных.

    Принимает multipart/form-data с полями 'file' и 'visibility'.
    Проверяет права доступа, размер и тип файла в зависимости от роли пользователя.
    После успешной загрузки запускает фоновую задачу для извлечения метаданных.
    """

    if current_user.role == UserRole.USER:
        if visibility != FileVisibility.PRIVATE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете загружать только приватные файлы!",
            )
        if file.content_type not in ALLOWED_FILE_TYPES_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы можете загружать только файлы в формате pdf!",
            )
        if file.size > MAX_FILE_SIZE_USER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_USER // 1024 // 1024}MB",
            )
    elif current_user.role == UserRole.MANAGER:
        if file.size > MAX_FILE_SIZE_MANAGER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_MANAGER // 1024 // 1024}MB",
            )
        if file.content_type not in ALLOWED_MIMETYPES_MANAGER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы можете загружать только файлы в формате pdf или docx!",
            )
    elif current_user.role == UserRole.ADMIN:
        if file.size > MAX_FILE_SIZE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_ADMIN // 1024 // 1024}MB",
            )
        if file.content_type not in ALLOWED_MIMETYPES_MANAGER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы можете загружать только файлы в формате pdf или docx!",
            )

    await file.seek(0)
    file_extension = file.filename.split(".")[-1]
    s3_obj_name = f"{uuid.uuid4()}.{file_extension}"

    upload_file_to_s3(settings, file.file, s3_obj_name)

    file_db = models.File(
        filename=file.filename,
        s3_path=s3_obj_name,
        visibility=visibility,
        owner_id=current_user.id,
        department_id=current_user.department_id,
    )
    db.add(file_db)
    await db.commit()
    await db.refresh(file_db)

    extract_metadata.delay(file_db.id)

    return file_db


@router.get(
    "/{file_id}", response_model=schemas.FileOut, status_code=status.HTTP_200_OK
)
async def get_file_info(file: models.File = Depends(get_file_for_user)):
    """
    Возвращает метаданные файла по его ID.

    Доступ к файлу проверяется на основе роли и отдела текущего пользователя.
    """

    return file


@router.get("/{file_id}/download")
async def download_file(
    file: models.File = Depends(get_file_for_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Генерирует временную ссылку и перенаправляет для скачивания файла.

    Увеличивает счетчик скачиваний файла.
    Доступ к файлу проверяется в зависимости `get_file_for_user`.
    """

    file.downloads += 1
    db.add(file)
    await db.commit()

    presigned_url = create_presigned_url(settings, file.s3_path)

    return RedirectResponse(presigned_url)


@router.get("/", response_model=list[schemas.FileOut], status_code=status.HTTP_200_OK)
async def list_files(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список файлов, доступных текущему пользователю.

    Фильтрация происходит на основе роли и отдела пользователя согласно ТЗ.
    Администратор видит все файлы.
    """

    query = select(models.File).options(selectinload(models.File.owner))

    if current_user.role == UserRole.MANAGER:
        query = query.where(
            or_(
                models.File.visibility == FileVisibility.PUBLIC,
                models.File.visibility == FileVisibility.DEPARTMENT,
            )
        )
    elif current_user.role == UserRole.USER:
        query = query.where(
            or_(
                models.File.visibility == FileVisibility.PUBLIC,
                and_(
                    models.File.visibility == FileVisibility.DEPARTMENT,
                    models.File.department_id == current_user.department_id,
                ),
                and_(
                    models.File.visibility == FileVisibility.PRIVATE,
                    models.File.owner_id == current_user.id,
                ),
            )
        )

    files_db = await db.execute(query)
    files = files_db.scalars().unique().all()

    return files


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_to_delete: models.File = Depends(get_file_to_delete),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Удаляет файл из S3 хранилища и из базы данных.

    Доступ на удаление проверяется в зависимости `get_file_to_delete`.
    """

    delete_file_from_s3(settings, file_to_delete.s3_path)

    await db.delete(file_to_delete)
    await db.commit()

    return
