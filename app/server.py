from fastapi import FastAPI
from app.routers.bitrix import router as bitrix_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

app.include_router(bitrix_router)


@app.get("/")
async def health_check():
    return {"status": "ok"}