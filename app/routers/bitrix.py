from fastapi import APIRouter, HTTPException, Request, status

from app.clients.bitrix_client import BitrixClient
from app.core.constants import BITRIX_CONTACT_EVENTS
from app.services.contact_service import (
    build_contact_update_fields,
    format_contact,
    should_update_contact_flag,
)

router = APIRouter(prefix="/webhook", tags=["Bitrix24"])


def extract_payload_value(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def get_contact_id(payload: dict) -> str | None:
    return (
        extract_payload_value(payload, "data[FIELDS][ID]")
        or extract_payload_value(payload, "data[FIELDS][ID][]")
    )


@router.post("/bitrix", status_code=status.HTTP_200_OK)
async def receive_bitrix_webhook(request: Request) -> dict:
    form = await request.form()
    payload = dict(form)

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

    if event_name not in BITRIX_CONTACT_EVENTS:
        return {"event": event_name, "ignored": True}

    bitrix_client = BitrixClient()

    contact_data = await bitrix_client.get_contact(contact_id)
    formatted_contact = format_contact(contact_data)

    if should_update_contact_flag(contact_data, formatted_contact["PHONE_WAS_CORRECTED"]):
        primary_phone = formatted_contact["PHONE"][0] if formatted_contact["PHONE"] else None
        fields = build_contact_update_fields(
            phone=primary_phone,
            phone_was_corrected=formatted_contact["PHONE_WAS_CORRECTED"],
        )
        await bitrix_client.update_contact(contact_id, fields)

    return {
        "event": event_name,
        "contact": formatted_contact,
    }