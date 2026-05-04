from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from app.auth.router import router as auth_router
from app.core.logger import setup_app_logging
from app.core.scheduler import scheduler, start_app_scheduler
from app.finance.router import router as finance_router
from app.license.router import router as license_router
from app.plan.router import router as plan_router
from app.user.router import router as user_router

# from scripts.generate_key_pairs import generate_production_keys


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 100

    setup_app_logging()
    start_app_scheduler()
    yield

    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
add_pagination(app)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(license_router)
app.include_router(plan_router)
app.include_router(finance_router)

# generate_production_keys()
