from app.core.constants import (
    BITRIX_FLAG_NO,
    BITRIX_FLAG_YES,
    CUSTOM_EMAIL_FIELD,
    PHONE_CORRECTED_FIELD,
)
from app.utils.phone import normalize_contact_phones


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

    return [
        email.get("VALUE", "")
        for email in contact_data_result.get("EMAIL", [])
        if email.get("VALUE")
    ]


def extract_raw_phones(contact_data_result: dict) -> list[str]:
    if not has_flag(contact_data_result.get("HAS_PHONE")):
        return []

    return [
        phone.get("VALUE")
        for phone in contact_data_result.get("PHONE", [])
        if phone.get("VALUE")
    ]


def format_contact(contact_data: dict) -> dict:
    contact = get_contact_result(contact_data)

    email = extract_contact_email(contact)
    raw_phones = extract_raw_phones(contact)
    normalized_phones, phone_was_corrected = normalize_contact_phones(raw_phones)

    return {
        "ID": contact.get("ID"),
        "NAME": contact.get("NAME"),
        "SECOND_NAME": contact.get("SECOND_NAME"),
        "LAST_NAME": contact.get("LAST_NAME"),
        "COMPANY_ID": contact.get("COMPANY_ID"),
        "HAS_PHONE": contact.get("HAS_PHONE"),
        "HAS_EMAIL": contact.get("HAS_EMAIL"),
        "EMAIL": email,
        "PHONE": normalized_phones,
        "PHONE_WAS_CORRECTED": phone_was_corrected,
    }


def should_update_contact_flag(contact_data: dict, phone_was_corrected: bool) -> bool:
    contact = get_contact_result(contact_data)
    expected_flag = BITRIX_FLAG_YES if phone_was_corrected else BITRIX_FLAG_NO
    return contact.get(PHONE_CORRECTED_FIELD) != expected_flag


def build_contact_update_fields(phone: str | None, phone_was_corrected: bool) -> dict:
    corrected_value = BITRIX_FLAG_YES if phone_was_corrected else BITRIX_FLAG_NO

    fields = {
        PHONE_CORRECTED_FIELD: corrected_value,
    }

    if phone:
        fields["PHONE"] = [
            {
                "VALUE": phone,
                "VALUE_TYPE": "WORK",
            }
        ]

    return fields