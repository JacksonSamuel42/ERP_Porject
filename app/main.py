from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio
from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.license.router import router as license_router
from app.plan.router import router as plan_router
from app.user.router import router as user_router

# from scripts.generate_key_pairs import generate_production_keys


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 100
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(license_router)
app.include_router(plan_router)

# generate_production_keys()
