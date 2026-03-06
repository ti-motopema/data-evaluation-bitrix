from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhook", tags=["Bitrix"])


@router.post("/bitrix24")
async def bitrix_webhook(request: Request):
    data = await request.json()

    print("Webhook recebido do Bitrix24:")
    print(data)

    event = data.get("event")
    payload = data.get("data")

    return {
        "status": "received",
        "event": event,
        "payload": payload
    }