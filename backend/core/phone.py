"""
Paddy Farming Assistant - E.164 Mobile Number Normalization & Validation Utility
Ensures all mobile numbers are strictly normalized to international E.164 standard.
"""

import re
from typing import Optional

# Strict E.164 regex: + followed by 1 to 3 digit country code and 7 to 14 digit subscriber number (total 8 to 15 digits)
E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")

# Indian mobile regex (10 digits starting with 6, 7, 8, 9)
INDIA_10DIGIT_REGEX = re.compile(r"^[6-9]\d{9}$")

# Full Indian mobile format in E.164: +91 followed by 10 digits starting with 6, 7, 8, or 9
INDIA_E164_REGEX = re.compile(r"^\+91[6-9]\d{9}$")


class InvalidMobileNumberError(ValueError):
    """Raised when a mobile number cannot be normalized to valid E.164 format."""
    pass


def normalize_mobile_number(raw_mobile: str, default_country_code: str = "+91") -> str:
    """
    Normalizes any valid local or international phone number to E.164 format.
    
    Rules:
    1. Removes all whitespace, hyphens, periods, parentheses.
    2. Converts leading '00' to '+'.
    3. If raw 10-digit Indian number (starts with 6-9), prepends default_country_code (+91).
    4. If raw 11-digit number starting with '0' followed by Indian 10 digits, strips '0' and prepends +91.
    5. If starts with '+', validates digits following '+'.
    6. Rejects any format that violates E.164 specifications.
    
    Returns:
        Clean E.164 string (e.g. '+919876543210')
        
    Raises:
        InvalidMobileNumberError: If the input is not a valid phone number.
    """
    if not raw_mobile or not isinstance(raw_mobile, str):
        raise InvalidMobileNumberError("Mobile number must be a non-empty string.")
    
    # Strip whitespace and formatting chars
    cleaned = re.sub(r"[\s\-\.\(\)]", "", raw_mobile.strip())
    
    if not cleaned:
        raise InvalidMobileNumberError("Mobile number contains no valid characters.")
    
    # Handle leading 00 as international prefix '+'
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
        
    # Handle Indian 10-digit local format: 9876543210 -> +919876543210
    if INDIA_10DIGIT_REGEX.match(cleaned):
        prefix = default_country_code if default_country_code.startswith("+") else f"+{default_country_code}"
        cleaned = f"{prefix}{cleaned}"
        
    # Handle Indian 11-digit format starting with 0: 09876543210 -> +919876543210
    elif cleaned.startswith("0") and INDIA_10DIGIT_REGEX.match(cleaned[1:]):
        prefix = default_country_code if default_country_code.startswith("+") else f"+{default_country_code}"
        cleaned = f"{prefix}{cleaned[1:]}"
        
    # Validate against E.164 regex
    if not E164_REGEX.match(cleaned):
        raise InvalidMobileNumberError(
            f"Invalid mobile number '{raw_mobile}'. Expected E.164 format e.g. '+919876543210'."
        )
        
    return cleaned


def is_valid_e164(mobile: str) -> bool:
    """Returns True if the string is already a strictly valid E.164 number."""
    if not mobile or not isinstance(mobile, str):
        return False
    return bool(E164_REGEX.match(mobile.strip()))


def validate_indian_mobile_number(raw_mobile: str) -> str:
    """
    Validates and normalizes an Indian mobile number to E.164 (+91XXXXXXXXXX).
    Rejects numbers that do not match the standard Indian mobile numbering plan
    (10 digits starting with 6, 7, 8, or 9).
    """
    if not raw_mobile or not isinstance(raw_mobile, str) or not raw_mobile.strip():
        raise InvalidMobileNumberError("Mobile number is required and cannot be empty.")
    normalized = normalize_mobile_number(raw_mobile, default_country_code="+91")
    if not INDIA_E164_REGEX.match(normalized):
        raise InvalidMobileNumberError(
            f"'{raw_mobile}' is not a valid Indian mobile number. "
            "Indian mobile numbers must be 10 digits starting with 6, 7, 8, or 9."
        )
    return normalized


