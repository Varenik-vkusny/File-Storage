from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from .config import get_settings

settings = get_settings()


SQLALCHEMY_DATABASE_URL = settings.sqlalchemy_database_url


async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)


AsyncLocalSession = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()