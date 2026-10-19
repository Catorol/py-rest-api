import logging
import time
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import tasks, users


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.access")

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        response.headers["X-Process-Time"] = f"{elapsed:.6f}"
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
        )
        return response

app = FastAPI(title="Task Manager")
app.add_middleware(TimingMiddleware)
app.include_router(users.router)
app.include_router(tasks.router)
