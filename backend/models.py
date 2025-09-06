from .database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from .roles import UserRole, FileVisibility


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(SQLAlchemyEnum(UserRole, name='userrole'), default=UserRole.USER, nullable=False)
    password_hash = Column(String)
    
    department_id = Column(Integer, ForeignKey('departments.id'))

    files = relationship('File', back_populates='owner', cascade="all, delete-orphan")
    department = relationship('Department', back_populates='users')


class Department(Base):
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

    users = relationship('User', back_populates='department')
    files = relationship('File', back_populates='department')

    


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    s3_path = Column(String, unique=True)
    visibility = Column(SQLAlchemyEnum(FileVisibility, name='filevisibility'), nullable=False)
    downloads = Column(Integer, default=0)

    page_count = Column(Integer, nullable=True)
    author = Column(String, nullable=True)
    # Здесь будут и другие метаданные

    owner_id = Column(Integer, ForeignKey('users.id'))
    department_id = Column(Integer, ForeignKey('departments.id'))

    owner = relationship('User', back_populates='files')
    department = relationship('Department', back_populates='files')