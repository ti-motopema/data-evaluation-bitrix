import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["Bitrix24"],
)


def extract_payload_value(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def get_contact_id(payload: dict) -> str | None:
    return (
        extract_payload_value(payload, "data[FIELDS][ID]")
        or extract_payload_value(payload, "data[FIELDS][ID][]")
    )


async def fetch_contact(contact_id: str) -> dict:
    url = f"{settings.BITRIX_WEBHOOK_URL}crm.contact.get.json"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data={"id": contact_id})
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as exc:
        logger.exception("Bitrix24 retornou erro HTTP ao buscar contato.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao consultar contato no Bitrix24.",
        ) from exc

    except httpx.RequestError as exc:
        logger.exception("Falha de comunicação com o Bitrix24.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha de comunicação com o Bitrix24.",
        ) from exc


@router.post("/bitrix", status_code=status.HTTP_200_OK)
async def receive_bitrix_webhook(request: Request) -> dict:
    form = await request.form()
    payload = dict(form)

    logger.info("Webhook Bitrix24 recebido: %s", payload)

    event_name = extract_payload_value(payload, "event")
    contact_id = get_contact_id(payload)

    if not event_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evento não informado.",
        )

    if not contact_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID do contato não informado.",
        )

    contact_data = await fetch_contact(contact_id)

    logger.info(
        "Evento processado com sucesso. event=%s contact_id=%s",
        event_name,
        contact_id,
    )
    logger.debug("Dados do contato retornados pelo Bitrix24: %s", contact_data)

    return {
        "ok": True,
        "event": event_name,
        "contact_id": contact_id,
        "contact": contact_data,
    }