import uuid
from fastapi import APIRouter, Depends, UploadFile, File as FastapiFile, HTTPException, status, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..s3_client import upload_file_to_s3, create_presigned_url, delete_file_from_s3
from ..roles import FileVisibility, UserRole
from ..dependencies import get_db, get_current_user, get_file_for_user, get_file_to_delete
from .. import models, schemas


router = APIRouter()


ALLOWED_FILE_TYPES_USER = ['application/pdf']

MAX_FILE_SIZE_USER = 10 * 1024 * 1024
MAX_FILE_SIZE_MANAGER = 50 * 1024 * 1024
MAX_FILE_SIZE_ADMIN = 100 * 1024 * 1024


@router.post('/upload', response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastapiFile(...),
    visibility: FileVisibility = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    
    if current_user.role == UserRole.USER:
        if visibility != FileVisibility.PRIVATE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Вы можете загружать только приватные файлы!'
            )
        
        if file.content_type not in ALLOWED_FILE_TYPES_USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Вы можете загружать только файлы в формате pdf!'
            )
        
        if file.size > MAX_FILE_SIZE_USER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f'Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_USER // 1024 // 1024}MB'
            )
        
    elif current_user.role == UserRole.MANAGER:
        if file.size > MAX_FILE_SIZE_MANAGER:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f'Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_MANAGER // 1024 // 1024}MB'
            )
        
    elif current_user.role == UserRole.ADMIN:
        if file.size > MAX_FILE_SIZE_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f'Размер файла слишком большой! Максимальный размер файла: {MAX_FILE_SIZE_ADMIN // 1024 // 1024}MB'
            )
        

    file_content = await file.read()

    await file.seek(0)

    file_extension = file.filename.split('.')[-1]
    s3_obj_name = f'{uuid.uuid4()}.{file_extension}'

    upload_file_to_s3(file.file, s3_obj_name)

    file_db = models.File(
        filename=file.filename,
        s3_path=s3_obj_name,
        visibility=visibility,
        owner_id=current_user.id,
        department_id=current_user.department_id
    )

    db.add(file_db)
    await db.commit()
    await db.refresh(file_db)

    return file_db


@router.get('/{file_id}', response_model=schemas.FileOut, status_code=status.HTTP_200_OK)
async def get_file_info(file: models.File = Depends(get_file_for_user)):

    return file


@router.get('/{file_id}/download')
async def download_file(file: models.File = Depends(get_file_for_user), db: AsyncSession = Depends(get_db)):

    file.downloads += 1
    db.add(file)
    await db.commit()

    presigned_url = create_presigned_url(file.s3_path)

    return RedirectResponse(presigned_url)



@router.get('/', response_model=list[schemas.FileOut], status_code=status.HTTP_200_OK)
async def list_files(current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):

    query = select(models.File).options(selectinload(models.File.owner))

    if current_user.role == UserRole.MANAGER:
        query = query.where(
            or_(
                models.File.visibility == FileVisibility.PUBLIC,
                models.File.visibility == FileVisibility.DEPARTMENT
            )
        )

    if current_user.role == UserRole.USER:
        query = query.where(
            or_(
                models.File.visibility == FileVisibility.PUBLIC,
                and_(
                    models.File.visibility == FileVisibility.DEPARTMENT,
                    models.File.department_id == current_user.id
                ),
                and_(
                    models.File.visibility == FileVisibility.PRIVATE,
                    models.File.owner_id == current_user.id
                )
            )
        )

    files_db = await db.execute(query)
    files = files_db.scalars().all()

    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Не найдено ни одного файла!'
        )
    return files



@router.delete('/{file_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_to_delete: models.File = Depends(get_file_to_delete), db: AsyncSession = Depends(get_db)):

    delete_file_from_s3(file_to_delete.s3_path)

    await db.delete(file_to_delete)
    await db.commit()

    return