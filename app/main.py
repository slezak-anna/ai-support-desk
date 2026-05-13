from fastapi import FastAPI

from app.api.tickets import router as tickets_router
from app.core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

@app.get("/")
def health_check():
    return {"status": "ok",
            "env": settings.app_env,
    }

app.include_router(tickets_router)