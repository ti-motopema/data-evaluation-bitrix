from fastapi import APIRouter, Request

router = APIRouter(
    prefix="/webhook",
    tags=["Bitrix24"]
)


@router.post("/bitrix")
async def receive_bitrix_webhook(request: Request):
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