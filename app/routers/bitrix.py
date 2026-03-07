import logging
import re

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


def validate_phone_number(phone: str) -> str | None:
    """
    Normaliza e valida números de telefone brasileiros.

    Formato final retornado:
    55 + DDD + 9 + número
    Exemplo: 5571999999999

    Retorna None caso o número seja inválido.
    """

    if not phone:
        return None

    # Remove qualquer caractere não numérico
    digits = re.sub(r"\D", "", phone)

    # Caso tenha 11 dígitos (DDD + número com 9)
    if len(digits) == 11:
        digits = "55" + digits

    # Caso tenha 10 dígitos (DDD + número antigo sem 9)
    elif len(digits) == 10:
        ddd = digits[:2]
        number = digits[2:]
        digits = f"55{ddd}9{number}"

    # Caso já tenha formato internacional
    elif len(digits) == 13 and digits.startswith("55"):
        ddd = digits[2:4]
        number = digits[4:]

        # garante o 9 após o DDD
        if not number.startswith("9"):
            number = "9" + number

        digits = f"55{ddd}{number}"

    else:
        return None

    # valida tamanho final
    if len(digits) != 13:
        return None

    return digits


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
    contact_data_result = contact_data.get("result", {})

    # print()
    # print()

    # print("Dados do contato retornados pelo Bitrix24: ", contact_data_result.get("EMAIL", ["NÃO VEIO DA PROP EMAIL"]))

    # print()
    # print()

    has_email = True if contact_data_result.get("HAS_EMAIL", None) == "Y" else False
    has_phone = True if contact_data_result.get("HAS_PHONE", None) == "Y" else False

    email = (
        contact_data_result.get("UF_CRM_CONTACT_1691011566947")
        or (([email.get("VALUE", "") for email in contact_data_result.get("EMAIL", [])]) if has_email else "")
    )
    phone = [phone.get("VALUE") for phone in contact_data_result.get("PHONE", [])] if has_phone else ""

    phone = [validate_phone_number(p) for p in phone]
    phone = [p for p in phone if p]

    contact_formatted = {
        "ID": contact_data_result.get("ID", None),
        "NAME": contact_data_result.get("NAME", None),
        "SECOND_NAME": contact_data_result.get("SECOND_NAME", None),
        "LAST_NAME": contact_data_result.get("LAST_NAME", None),
        "COMPANY_ID": contact_data_result.get("COMPANY_ID", None),
        "HAS_PHONE": contact_data_result.get("HAS_PHONE", None),
        "HAS_EMAIL": contact_data_result.get("HAS_EMAIL", None),
        "EMAIL": email,
        "PHONE": phone,
    }


    # print("Contato formatado para processamento: ", contact_formatted)
    # print("Números de telefone validados: ", phone)

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