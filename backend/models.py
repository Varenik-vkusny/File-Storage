from .database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    password_hash = Column(String)
    
    department_id = Column(Integer, ForeignKey('departments.id'))

    file = relationship('File', back_populates='owner')
    department = relationship('Department', back_populates='users')


class Department(Base):
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)

    users = relationship('User', back_populates='department')

    


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    s3_path = Column(String)
    visibility = Column(String)

    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User', back_populates='file')