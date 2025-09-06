from pydantic import BaseModel, ConfigDict
from typing import Optional
from .roles import UserRole, FileVisibility


class UserIn(BaseModel):
    username: str
    password: str
    department_id: int


class DepartmentOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole

    department: DepartmentOut | None = None

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: UserRole


class FileOut(BaseModel):
    id: int
    filename: str
    visibility: FileVisibility
    department_id: int | None = None

    # Метаданные
    author: str | None = None
    title: str | None = None
    created_date: str | None = None
    page_count: int | None = None
    creator_tool: str | None = None
    paragraph_count: int | None = None
    table_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
