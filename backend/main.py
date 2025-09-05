from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix='/auth', tags=['Authentication'])
app.include_router(users.router, prefix='/users', tags=['Users'])


@app.get('/')
async def Hello():
    return {'message': 'Hello World'}