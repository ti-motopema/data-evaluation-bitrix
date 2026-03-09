import httpx
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.utils.phone import normalize_contact_phones
from app.core.constants import CUSTOM_EMAIL_FIELD, PHONE_CORRECTED_FIELD, BITRIX_FLAG_NO, BITRIX_FLAG_YES, BITRIX_CONTACT_EVENTS


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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao consultar contato no Bitrix24.",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha de comunicacao com o Bitrix24.",
        ) from exc


def should_update_contact_flag(contact_data: dict, phone_was_corrected: bool) -> bool:
    contact_data_result = get_contact_result(contact_data)
    expected_flag = BITRIX_FLAG_YES if phone_was_corrected else BITRIX_FLAG_NO
    return contact_data_result.get(PHONE_CORRECTED_FIELD) != expected_flag


def get_contact_result(contact_data: dict) -> dict:
    return contact_data.get("result", {})


def has_flag(value: str | None) -> bool:
    return value == "Y"


def extract_contact_email(contact_data_result: dict) -> str | list[str]:
    custom_email = contact_data_result.get(CUSTOM_EMAIL_FIELD)
    if custom_email:
        return custom_email

    if not has_flag(contact_data_result.get("HAS_EMAIL")):
        return ""

    return [email.get("VALUE", "") for email in contact_data_result.get("EMAIL", [])]


def extract_raw_phones(contact_data_result: dict) -> list[str]:
    if not has_flag(contact_data_result.get("HAS_PHONE")):
        return []

    return [phone.get("VALUE") for phone in contact_data_result.get("PHONE", []) if phone.get("VALUE")]


def filter_useful_properties(contact_data: dict) -> dict:
    contact_data_result = get_contact_result(contact_data)

    email = extract_contact_email(contact_data_result)
    raw_phones = extract_raw_phones(contact_data_result)
    normalized_phones, phone_was_corrected = normalize_contact_phones(raw_phones)

    return {
        "ID": contact_data_result.get("ID", None),
        "NAME": contact_data_result.get("NAME", None),
        "SECOND_NAME": contact_data_result.get("SECOND_NAME", None),
        "LAST_NAME": contact_data_result.get("LAST_NAME", None),
        "COMPANY_ID": contact_data_result.get("COMPANY_ID", None),
        "HAS_PHONE": contact_data_result.get("HAS_PHONE", None),
        "HAS_EMAIL": contact_data_result.get("HAS_EMAIL", None),
        "EMAIL": email,
        "PHONE": normalized_phones,
        "PHONE_WAS_CORRECTED": phone_was_corrected,
    }


async def update_contact_phone_field(contact_id: str, phone: str | None, phone_was_corrected: bool) -> dict:
    url = f"{settings.BITRIX_WEBHOOK_URL}crm.contact.update.json"
    corrected_value = BITRIX_FLAG_YES if phone_was_corrected else BITRIX_FLAG_NO

    payload = {
        "id": contact_id,
        "fields": {
            PHONE_CORRECTED_FIELD: corrected_value,
        },
    }

    if phone:
        payload["fields"]["PHONE"] = [
            {
                "VALUE": phone,
                "VALUE_TYPE": "WORK",
            }
        ]

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    return response.json()


@router.post("/bitrix", status_code=status.HTTP_200_OK)
async def receive_bitrix_webhook(request: Request) -> dict:
    form = await request.form()
    payload = dict(form)

    event_name = extract_payload_value(payload, "event")
    contact_id = get_contact_id(payload)

    if not event_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evento nao informado.",
        )

    if not contact_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID do contato nao informado.",
        )

    if event_name not in BITRIX_CONTACT_EVENTS:
        return {"event": event_name, "ignored": True}

    contact_data = await fetch_contact(contact_id)
    contact_formatted = filter_useful_properties(contact_data)

    if should_update_contact_flag(contact_data, contact_formatted["PHONE_WAS_CORRECTED"]):
        primary_phone = contact_formatted["PHONE"][0] if contact_formatted["PHONE"] else None
        await update_contact_phone_field(contact_id, primary_phone, contact_formatted["PHONE_WAS_CORRECTED"])

    return {
        "event": event_name,
        "contact": contact_formatted,
    }
