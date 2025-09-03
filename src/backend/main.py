from fastapi import FastAPI
from contextlib import asynccontextmanager

app = FastAPI()


@asynccontextmanager
async def lifespan(app=app):

    yield

    