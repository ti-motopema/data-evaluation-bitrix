import re

def is_phone_in_target_format(digits: str) -> bool:
    return len(digits) == 13 and digits.startswith("55") and digits[4:5] == "9"


def normalize_phone_number(phone: str) -> tuple[str | None, bool]:
    if not phone:
        return None, False

    digits = re.sub(r"\D", "", phone)

    if is_phone_in_target_format(digits):
        return digits, False

    if len(digits) == 11:
        return f"55{digits}", True

    if len(digits) == 10:
        ddd = digits[:2]
        number = digits[2:]
        return f"55{ddd}9{number}", True

    if len(digits) == 13 and digits.startswith("55"):
        ddd = digits[2:4]
        number = digits[4:]
        if number.startswith("9"):
            return digits, False
        return f"55{ddd}9{number}", True

    return None, False


def normalize_contact_phones(raw_phones: list[str]) -> tuple[list[str], bool]:
    normalized_phones: list[str] = []
    phone_was_corrected = False

    for phone in raw_phones:
        normalized_phone, corrected = normalize_phone_number(phone)
        if normalized_phone:
            normalized_phones.append(normalized_phone)
            phone_was_corrected = phone_was_corrected or corrected

    return normalized_phones, phone_was_corrected