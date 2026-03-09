import httpx
from fastapi import HTTPException, status

from app.core.config import settings

class BitrixClient:
    def __init__(self) -> None:
        self.base_url = settings.BITRIX_WEBHOOK_URL
        self.timeout = 20

    async def get_contact(self, contact_id: str) -> dict:
        url = f"{self.base_url}crm.contact.get.json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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
                detail="Falha de comunicação com o Bitrix24.",
            ) from exc

    async def update_contact(self, contact_id: str, fields: dict) -> dict:
        url = f"{self.base_url}crm.contact.update.json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={"id": contact_id, "fields": fields},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Erro ao atualizar contato no Bitrix24.",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Falha de comunicação com o Bitrix24.",
            ) from exc