"""
PII Format Validators

Validation functions for various PII formats including
Aadhaar checksum validation and PAN format verification.
"""

import re
from typing import Tuple


def validate_aadhaar(aadhaar: str) -> Tuple[bool, str]:
    """
    Validate an Aadhaar number format and checksum.
    
    Aadhaar uses Verhoeff algorithm for checksum validation.
    Format: 12 digits, first digit cannot be 0 or 1.
    
    Args:
        aadhaar: The Aadhaar number to validate (with or without spaces)
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Remove spaces and hyphens
    clean = re.sub(r'[\s\-]', '', aadhaar)
    
    # Check length
    if len(clean) != 12:
        return False, f"Invalid length: expected 12 digits, got {len(clean)}"
    
    # Check if all digits
    if not clean.isdigit():
        return False, "Aadhaar must contain only digits"
    
    # First digit cannot be 0 or 1
    if clean[0] in '01':
        return False, "First digit cannot be 0 or 1"
    
    # Verhoeff algorithm tables
    d_table = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]
    
    p_table = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]
    
    # Validate checksum using Verhoeff algorithm
    c = 0
    reversed_digits = [int(d) for d in reversed(clean)]
    for i, digit in enumerate(reversed_digits):
        c = d_table[c][p_table[i % 8][digit]]
    
    if c != 0:
        return False, "Invalid checksum"
    
    return True, "Valid Aadhaar format"


def validate_aadhaar_format_only(aadhaar: str) -> Tuple[bool, str]:
    """
    Validate Aadhaar format without checksum (for synthetic data).
    
    Args:
        aadhaar: The Aadhaar number to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    clean = re.sub(r'[\s\-]', '', aadhaar)
    
    if len(clean) != 12:
        return False, f"Invalid length: expected 12 digits, got {len(clean)}"
    
    if not clean.isdigit():
        return False, "Aadhaar must contain only digits"
    
    if clean[0] in '01':
        return False, "First digit cannot be 0 or 1"
    
    return True, "Valid Aadhaar format"


def validate_pan(pan: str) -> Tuple[bool, str]:
    """
    Validate a PAN (Permanent Account Number) format.
    
    Format: AAAAA0000A
    - First 3 characters: Alphabetic (AAA to ZZZ)
    - 4th character: Entity type (P=Person, C=Company, H=HUF, etc.)
    - 5th character: First letter of surname/name
    - Next 4 characters: Sequential digits (0001 to 9999)
    - Last character: Alphabetic check digit
    
    Args:
        pan: The PAN to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Remove spaces
    clean = pan.strip().upper()
    
    # Check length
    if len(clean) != 10:
        return False, f"Invalid length: expected 10 characters, got {len(clean)}"
    
    # PAN pattern: 5 letters + 4 digits + 1 letter
    pattern = r'^[A-Z]{3}[ABCFGHLJPTK][A-Z][0-9]{4}[A-Z]$'
    
    if not re.match(pattern, clean):
        # More specific error messages
        if not clean[:3].isalpha():
            return False, "First 3 characters must be letters"
        if clean[3] not in 'ABCFGHLJPTK':
            return False, f"4th character '{clean[3]}' is not a valid entity type"
        if not clean[4].isalpha():
            return False, "5th character must be a letter"
        if not clean[5:9].isdigit():
            return False, "Characters 6-9 must be digits"
        if not clean[9].isalpha():
            return False, "Last character must be a letter"
        return False, "Invalid PAN format"
    
    return True, "Valid PAN format"


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.
    
    Args:
        email: The email address to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, "Valid email format"


def validate_phone_indian(phone: str) -> Tuple[bool, str]:
    """
    Validate Indian phone number format.
    
    Args:
        phone: The phone number to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Remove common separators
    clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Remove country code if present
    if clean.startswith('91'):
        clean = clean[2:]
    
    # Should be 10 digits starting with 6, 7, 8, or 9
    if len(clean) != 10:
        return False, f"Invalid length: expected 10 digits, got {len(clean)}"
    
    if not clean.isdigit():
        return False, "Phone number must contain only digits"
    
    if clean[0] not in '6789':
        return False, "Indian mobile numbers must start with 6, 7, 8, or 9"
    
    return True, "Valid Indian phone number"


def validate_phone_us(phone: str) -> Tuple[bool, str]:
    """
    Validate US phone number format.
    
    Args:
        phone: The phone number to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Remove common separators
    clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Remove country code if present
    if clean.startswith('1'):
        clean = clean[1:]
    
    # Should be 10 digits
    if len(clean) != 10:
        return False, f"Invalid length: expected 10 digits, got {len(clean)}"
    
    if not clean.isdigit():
        return False, "Phone number must contain only digits"
    
    return True, "Valid US phone number"


def validate_ssn(ssn: str) -> Tuple[bool, str]:
    """
    Validate US Social Security Number format.
    
    Format: XXX-XX-XXXX
    - Area number (first 3): 001-899 (excluding 666)
    - Group number (middle 2): 01-99
    - Serial number (last 4): 0001-9999
    
    Args:
        ssn: The SSN to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Check format with dashes
    pattern = r'^\d{3}-\d{2}-\d{4}$'
    
    if not re.match(pattern, ssn):
        return False, "Invalid SSN format (expected XXX-XX-XXXX)"
    
    # Parse parts
    parts = ssn.split('-')
    area = int(parts[0])
    group = int(parts[1])
    serial = int(parts[2])
    
    # Validate area number
    if area == 0 or area == 666 or area > 899:
        return False, "Invalid area number"
    
    # Validate group number
    if group == 0:
        return False, "Invalid group number"
    
    # Validate serial number
    if serial == 0:
        return False, "Invalid serial number"
    
    return True, "Valid SSN format"


def validate_credit_card(card_number: str) -> Tuple[bool, str]:
    """
    Validate credit card number using Luhn algorithm.
    
    Args:
        card_number: The credit card number to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Remove spaces and dashes
    clean = re.sub(r'[\s\-]', '', card_number)
    
    # Check if all digits
    if not clean.isdigit():
        return False, "Card number must contain only digits"
    
    # Check length (13-19 digits for most cards)
    if len(clean) < 13 or len(clean) > 19:
        return False, f"Invalid length: {len(clean)} digits"
    
    # Luhn algorithm
    def luhn_check(number: str) -> bool:
        digits = [int(d) for d in number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        return checksum % 10 == 0
    
    if not luhn_check(clean):
        return False, "Invalid checksum (Luhn check failed)"
    
    return True, "Valid credit card number"


# Validator registry
VALIDATORS = {
    "IN_AADHAAR": validate_aadhaar_format_only,
    "IN_PAN": validate_pan,
    "EMAIL_ADDRESS": validate_email,
    "PHONE_NUMBER": validate_phone_indian,
    "US_SSN": validate_ssn,
    "CREDIT_CARD": validate_credit_card,
}


def validate_entity(entity_type: str, value: str) -> Tuple[bool, str]:
    """
    Validate an entity value based on its type.
    
    Args:
        entity_type: The type of entity
        value: The value to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    validator = VALIDATORS.get(entity_type)
    if validator is None:
        return True, f"No validator for {entity_type}"
    return validator(value)

