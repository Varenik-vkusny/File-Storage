from enum import Enum

class UserRole(str, Enum):
    USER = 'user'
    MANAGER = 'manager'
    ADMIN = 'admin'

class FileVisibility(str, Enum):
    PRIVATE = 'private'
    DEPARTMENT = 'department'
    PUBLIC = 'public'