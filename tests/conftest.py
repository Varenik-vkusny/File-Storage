import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from backend.main import app
from backend.database import Base
from backend.dependencies import get_db
from backend.config import get_settings, get_test_settings
from backend import models
from backend.roles import UserRole

# --- НАСТРОЙКА ТЕСТОВОГО ОКРУЖЕНИЯ ---

# Глобально подменяем зависимость get_settings на get_test_settings.
# Теперь все приложение во время тестов будет использовать тестовую конфигурацию
# (in-memory БД, тестовые ключи, localhost для S3 и т.д.).
app.dependency_overrides[get_settings] = get_test_settings

# URL для in-memory базы данных SQLite, которая работает в асинхронном режиме.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Создаем тестовый асинхронный движок SQLAlchemy.
test_async_engine = create_async_engine(TEST_DATABASE_URL)

# Создаем фабрику сессий для тестов.
TestAsyncSessionLocal = sessionmaker(
    bind=test_async_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость-заменитель для get_db.
    Предоставляет тестовую сессию БД, которая откатывает все изменения после теста.
    """

    async with TestAsyncSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True, scope="function")
async def prepare_database():
    """
    Фикстура, которая выполняется для КАЖДОГО теста (autouse=True).
    Создает все таблицы перед тестом и удаляет их после.
    Гарантирует, что каждый тест работает с чистой базой данных.
    """

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Обязательная фикстура для работы pytest с asyncio.
    Указывает, какой асинхронный "бэкенд" использовать.
    """

    return "asyncio"


# --- ФИКТУРЫ ДЛЯ КЛИЕНТОВ И ПОЛЬЗОВАТЕЛЕЙ ---


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Базовая фикстура, предоставляющая анонимный (неаутентифицированный)
    HTTP-клиент для взаимодействия с приложением.
    """

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Фикстура, предоставляющая прямую сессию к тестовой БД.
    Полезна для подготовки данных перед тестом.
    """

    async with TestAsyncSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> models.User:
    """Создает и возвращает обычного пользователя (role='user') в тестовой БД."""

    from backend.security import hash_password

    user = models.User(
        username="testuser",
        password_hash=hash_password("testpassword"),
        role=UserRole.USER,
        department_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture(scope="function")
async def test_admin(db_session: AsyncSession) -> models.User:
    """Создает и возвращает администратора (role='admin') в тестовой БД."""

    from backend.security import hash_password

    user = models.User(
        username="testadmin",
        password_hash=hash_password("testpassword"),
        role=UserRole.ADMIN,
        department_id=5,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture(scope="function")
async def test_manager(db_session: AsyncSession) -> models.User:
    """Создает и возвращает менеджера (role='manager') в тестовой БД."""

    from backend.security import hash_password

    user = models.User(
        username="testmanager",
        password_hash=hash_password("testpassword"),
        role=UserRole.MANAGER,
        department_id=2,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture(scope="function")
async def authenticated_client_user(
    client: AsyncClient, test_user: models.User
) -> AsyncClient:
    """Возвращает HTTP-клиент, аутентифицированный как обычный пользователь."""

    data = {"username": test_user.username, "password": "testpassword"}
    response = await client.post("/auth/login", data=data)
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="function")
async def authenticated_client_admin(
    client: AsyncClient, test_admin: models.User
) -> AsyncClient:
    """Возвращает HTTP-клиент, аутентифицированный как администратор."""

    data = {"username": test_admin.username, "password": "testpassword"}
    response = await client.post("/auth/login", data=data)
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="function")
async def authenticated_client_manager(
    client: AsyncClient, test_manager: models.User
) -> AsyncClient:
    """Возвращает HTTP-клиент, аутентифицированный как менеджер."""

    data = {"username": test_manager.username, "password": "testpassword"}
    response = await client.post("/auth/login", data=data)
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture(scope="function")
async def test_another_user(db_session: AsyncSession) -> models.User:
    """Создает и возвращает второго обычного пользователя для тестов доступа."""

    from backend.security import hash_password

    user = models.User(
        username="testanotheruser",
        password_hash=hash_password("testpassword"),
        role=UserRole.USER,
        department_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture(scope="function")
async def authenticated_client_another_user(
    client: AsyncClient, test_another_user: models.User
) -> AsyncClient:
    """Возвращает HTTP-клиент, аутентифицированный как второй обычный пользователь."""

    data = {"username": test_another_user.username, "password": "testpassword"}
    response = await client.post("/auth/login", data=data)
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
