from .database import AsyncLocalSession

async def get_db():
    async with AsyncLocalSession() as session:
        yield session