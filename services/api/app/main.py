from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.services.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title=settings.app_name, version="0.1.0")
frontend_origin = settings.frontend_url.rstrip("/")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def start_background_scheduler() -> None:
    start_scheduler()


@app.on_event("shutdown")
def stop_background_scheduler() -> None:
    stop_scheduler()
