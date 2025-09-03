from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)


@app.get('/')
async def Hello():
    return {'message': 'Hello World'}