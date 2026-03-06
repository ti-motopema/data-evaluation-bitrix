from fastapi import FastAPI
from src.api.bitrix_webhook import router as bitrix_router
from core import settings

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

app.include_router(bitrix_router)


@app.get("/")
def health_check():
    return {"status": "running"}