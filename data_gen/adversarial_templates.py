"""
Adversarial and Ambiguous Templates for Robust PII Detection

Contains templates for:
- Evasion attempts (users trying to bypass detection)
- Contextual ambiguity (PII-like patterns in non-PII contexts)
- OCR/scan artifacts
- Informal/chat-style text
- Multi-language mixing
- Dangerous negatives (false positive traps)
"""

from typing import List, Dict, Tuple
import random

# ============================================================================
# Evasion Attempt Templates (Adversarial)
# ============================================================================

EVASION_TEMPLATES: List[str] = [
    # Spacing evasion
    "my a a d h a a r is {IN_AADHAAR}",
    "p a n number: {IN_PAN}",
    "e m a i l: {EMAIL_ADDRESS}",
    "call me at {PHONE_NUMBER} (mobile)",
    
    # Written out numbers
    "aadhaar: two three four five six seven eight nine zero one two three",
    "my pan is A B C P D one two three four E",
    
    # Mixed separators
    "aadhaar no. {IN_AADHAAR} (verified)",
    "PAN-Card: {IN_PAN}",
    "email_id={EMAIL_ADDRESS}",
    "ph:{PHONE_NUMBER}",
    
    # Obfuscation with brackets/symbols
    "aadhaar [HIDDEN] {IN_AADHAAR} [/HIDDEN]",
    "PAN: <{IN_PAN}>",
    "email: ({EMAIL_ADDRESS})",
    "***{PHONE_NUMBER}***",
    
    # Reverse/encoded
    "my aadhaar (reversed): {IN_AADHAAR}",  # Note: actual value not reversed
    "pan_base64: {IN_PAN}",  # Not actually encoded
    
    # Split across lines (simulated)
    "Aadhaar: {IN_AADHAAR} (line 1)",
    "continued from above... PAN {IN_PAN}",
    
    # Leetspeak-style
    "4adh44r: {IN_AADHAAR}",
    "p4n c4rd: {IN_PAN}",
    "3m41l: {EMAIL_ADDRESS}",
    
    # Unicode lookalikes (using regular chars but mentioning unicode)
    "aadhaar (unicode): {IN_AADHAAR}",
    "PAN [special chars]: {IN_PAN}",
]

# ============================================================================
# OCR/Scan Artifact Templates
# ============================================================================

OCR_ARTIFACT_TEMPLATES: List[str] = [
    # Typical OCR errors
    "Aadhaar No: {IN_AADHAAR} [scanned]",
    "PAN Card: {IN_PAN} (from document)",
    "Email: {EMAIL_ADDRESS} [OCR]",
    "Mobile: {PHONE_NUMBER} (scanned copy)",
    
    # With noise indicators
    "Aadhaar: {IN_AADHAAR} [quality: poor]",
    "PAN: {IN_PAN} [partially visible]",
    "Contact: {EMAIL_ADDRESS} [blurry scan]",
    
    # Form-like structure
    "Field: Aadhaar Number | Value: {IN_AADHAAR}",
    "PAN_CARD_NO: {IN_PAN}",
    "EMAIL_ADDRESS_FIELD: {EMAIL_ADDRESS}",
    "MOBILE_NO: {PHONE_NUMBER}",
    
    # Table-like
    "| Aadhaar | {IN_AADHAAR} |",
    "| PAN | {IN_PAN} |",
    "| Email | {EMAIL_ADDRESS} |",
    "| Phone | {PHONE_NUMBER} |",
    
    # With line noise
    "Aadhaar..... {IN_AADHAAR}",
    "PAN_______ {IN_PAN}",
    "Email --- {EMAIL_ADDRESS}",
    "Ph: .... {PHONE_NUMBER}",
]

# ============================================================================
# Informal/Chat Style Templates
# ============================================================================

INFORMAL_TEMPLATES: List[str] = [
    # SMS/Chat style
    "hey my aadhaar is {IN_AADHAAR} pls verify",
    "pan - {IN_PAN} chk it",
    "mail me @ {EMAIL_ADDRESS} asap",
    "cal {PHONE_NUMBER} urgent!!!",
    
    # With typos/shortcuts
    "aadhar no {IN_AADHAAR} plz update",
    "my pan card {IN_PAN} for kyc",
    "email id {EMAIL_ADDRESS} thnx",
    "mob no {PHONE_NUMBER} call me",
    
    # Emoji-adjacent (without actual emojis)
    "aadhaar: {IN_AADHAAR} :)",
    "pan {IN_PAN} done!",
    "{EMAIL_ADDRESS} - contact me here!",
    "ring me {PHONE_NUMBER} anytime",
    
    # Very casual
    "so my aadhaar is like {IN_AADHAAR} or smth",
    "pan? its {IN_PAN}",
    "just email {EMAIL_ADDRESS} whenever",
    "hmu at {PHONE_NUMBER}",
    
    # With filler words
    "umm my aadhaar number is {IN_AADHAAR} i think",
    "so like my pan is {IN_PAN} yeah",
    "email me at like {EMAIL_ADDRESS} or whatever",
    "you can call {PHONE_NUMBER} i guess",
]

# ============================================================================
# Hinglish (Hindi-English Mix) Templates
# ============================================================================

HINGLISH_TEMPLATES: List[str] = [
    # Aadhaar
    "mera aadhaar number hai {IN_AADHAAR}",
    "aadhaar card ka number: {IN_AADHAAR}",
    "yeh mera aadhaar hai {IN_AADHAAR}",
    "aadhaar no. {IN_AADHAAR} hai mera",
    "mera uid {IN_AADHAAR} hai",
    
    # PAN
    "mera pan card {IN_PAN} hai",
    "pan number: {IN_PAN} tax ke liye",
    "yeh pan hai {IN_PAN}",
    "income tax pan {IN_PAN}",
    
    # Email
    "email kar do {EMAIL_ADDRESS} pe",
    "mera email id {EMAIL_ADDRESS} hai",
    "mail karo {EMAIL_ADDRESS}",
    "email address: {EMAIL_ADDRESS} hai",
    
    # Phone
    "phone karo {PHONE_NUMBER} pe",
    "mera number hai {PHONE_NUMBER}",
    "call kar {PHONE_NUMBER}",
    "mobile no. {PHONE_NUMBER}",
    
    # Mixed
    "name {PERSON} hai aur aadhaar {IN_AADHAAR}",
    "{PERSON} ka pan {IN_PAN} hai",
    "contact: {PERSON} - {EMAIL_ADDRESS}",
]

# ============================================================================
# Contextual Ambiguity Templates (Tricky Positives)
# ============================================================================

AMBIGUOUS_POSITIVE_TEMPLATES: List[str] = [
    # Aadhaar in unusual context
    "The identifier {IN_AADHAAR} was used for verification",
    "System logged {IN_AADHAAR} as input",
    "Value received: {IN_AADHAAR}",
    "String '{IN_AADHAAR}' matches pattern",
    "Input: {IN_AADHAAR} (12 digits)",
    
    # PAN in unusual context
    "Code {IN_PAN} was submitted",
    "The alphanumeric {IN_PAN} is registered",
    "Entry: {IN_PAN}",
    "Received: {IN_PAN}",
    
    # Email in unusual context
    "String '{EMAIL_ADDRESS}' is valid",
    "Format check passed: {EMAIL_ADDRESS}",
    "Value={EMAIL_ADDRESS}",
    "Input email: {EMAIL_ADDRESS}",
    
    # Phone in unusual context
    "Number {PHONE_NUMBER} recorded",
    "Digits: {PHONE_NUMBER}",
    "Numeric input: {PHONE_NUMBER}",
    
    # Without explicit context words
    "{IN_AADHAAR}",
    "{IN_PAN}",
    "{EMAIL_ADDRESS}",
    "{PHONE_NUMBER}",
    "({IN_AADHAAR})",
    "[{IN_PAN}]",
]

# ============================================================================
# Dangerous Negative Templates (Should NOT flag)
# ============================================================================

DANGEROUS_NEGATIVE_TEMPLATES: List[str] = [
    # 12-digit numbers that aren't Aadhaar
    "Order ID: 0123 4567 8901",  # Starts with 0
    "Transaction: 1234 5678 9012",  # Starts with 1
    "Reference: 0000 0000 0000",  # All zeros
    "Booking number 1111 2222 3333",
    "Invoice #: 0987 6543 2109",
    "Ticket ID: 1000 2000 3000",
    "Confirmation: 0012 3456 7890",
    
    # PAN-like codes that aren't PAN
    "Product: ABCDE12345",  # Wrong format (5 letters + 5 digits)
    "SKU: ABCXY1234Z",  # Invalid 4th character
    "Model: XYZDE9999X",  # Invalid 4th character (D)
    "Part: ABCDE1234",  # Only 9 characters
    "Serial: ABCDE12345F",  # 11 characters
    "Code: abcpd1234e",  # Lowercase (ambiguous)
    
    # Phone-like numbers that aren't phones
    "Account: 0123456789",  # Starts with 0
    "Policy: 1234567890",  # Starts with 1
    "Member ID: 5432109876",  # Starts with 5
    "Registration: 0000000000",
    "License: 1111111111",
    
    # Email-like text that isn't email
    "Use format: user@domain",
    "Pattern: name@company.com",
    "Example: test@example",
    "Template: {user}@{domain}.{tld}",
    "Syntax: local@host",
    "Format should be x@y.z",
    
    # SSN-like numbers that aren't SSN
    "Code: 000-00-0000",  # Invalid area
    "Format: 666-12-3456",  # Invalid area (666)
    "Pattern: 900-00-0000",  # Invalid area (900+)
    "Version: 123-00-4567",  # Invalid group (00)
    "ID: 123-45-0000",  # Invalid serial (0000)
    
    # Date formats that look like numbers
    "Date: 12-34-5678",
    "DOB: 01/02/1990",
    "Expiry: 2025-12-31",
    "Valid until: 31-12-2025",
    
    # IP addresses
    "Server: 192.168.1.100",
    "Gateway: 10.0.0.1",
    "Host: 172.16.0.50",
    
    # Version numbers
    "Version 1.2.3.4",
    "Release: 2.0.0.1",
    "Build: 10.0.19041",
    
    # Coordinates
    "Location: 28.6139, 77.2090",
    "GPS: 19.0760° N, 72.8777° E",
    
    # Generic codes
    "Promo: SAVE20NOW",
    "Coupon: FLAT50OFF",
    "Voucher: ABC123XYZ",
    "PIN: 123456",
    "OTP: 987654",
    
    # Measurements/Quantities
    "Weight: 1234.5678 kg",
    "Amount: 9876543210",
    "Quantity: 1000000000",
    "Price: 12345.67",
]

# ============================================================================
# Multi-PII with Noise Templates
# ============================================================================

MULTI_PII_NOISY_TEMPLATES: List[str] = [
    # Multiple entities with informal style
    "hey {PERSON} here, aadhaar {IN_AADHAAR}, pan {IN_PAN}, mail {EMAIL_ADDRESS}",
    "details: name-{PERSON}, aadhar-{IN_AADHAAR}, email-{EMAIL_ADDRESS}",
    "{PERSON}'s info >>> aadhaar:{IN_AADHAAR} pan:{IN_PAN} mob:{PHONE_NUMBER}",
    
    # Form-like with noise
    "Name: {PERSON} | Aadhaar: {IN_AADHAAR} | PAN: {IN_PAN}",
    "[{PERSON}] [{IN_AADHAAR}] [{IN_PAN}] [{EMAIL_ADDRESS}]",
    "User={PERSON}; Aadhaar={IN_AADHAAR}; Email={EMAIL_ADDRESS}",
    
    # Mixed context
    "Contact {PERSON} at {EMAIL_ADDRESS} or {PHONE_NUMBER} (aadhaar: {IN_AADHAAR})",
    "KYC: {PERSON}, {IN_AADHAAR}, {IN_PAN}, {PHONE_NUMBER}, {EMAIL_ADDRESS}",
    
    # With OCR-style formatting
    "Name..... {PERSON}\nAadhaar.. {IN_AADHAAR}\nPAN...... {IN_PAN}",
    "| {PERSON} | {IN_AADHAAR} | {IN_PAN} | {EMAIL_ADDRESS} |",
]

# ============================================================================
# Partial/Masked PII Templates (Should still flag)
# ============================================================================

PARTIAL_PII_TEMPLATES: List[str] = [
    # Partially masked but still identifiable
    "Aadhaar ending in XXXX XXXX {LAST4_AADHAAR}",
    "PAN: XXXXX{LAST5_PAN}",
    "Email: ***@{EMAIL_DOMAIN}",
    "Phone: XXXXXX{LAST4_PHONE}",
    
    # With visible portions
    "Aadhaar: {FIRST4_AADHAAR} **** ****",
    "PAN starts with {FIRST5_PAN}****",
    "Mobile ending {LAST4_PHONE}",
    
    # Redacted style
    "Aadhaar: [REDACTED] {LAST4_AADHAAR}",
    "PAN: {FIRST5_PAN}[HIDDEN]",
    "Contact: {FIRST_CHAR_EMAIL}***@***",
]

# ============================================================================
# Template Combination Helpers
# ============================================================================

ALL_ADVERSARIAL_TEMPLATES: List[str] = (
    EVASION_TEMPLATES + 
    OCR_ARTIFACT_TEMPLATES + 
    INFORMAL_TEMPLATES + 
    HINGLISH_TEMPLATES +
    AMBIGUOUS_POSITIVE_TEMPLATES +
    MULTI_PII_NOISY_TEMPLATES
)

ALL_DANGEROUS_NEGATIVES: List[str] = DANGEROUS_NEGATIVE_TEMPLATES


def get_random_adversarial_template() -> str:
    """Get a random adversarial template."""
    return random.choice(ALL_ADVERSARIAL_TEMPLATES)


def get_random_dangerous_negative() -> str:
    """Get a random dangerous negative template."""
    return random.choice(ALL_DANGEROUS_NEGATIVES)


def get_template_by_difficulty(difficulty: str = "medium") -> str:
    """
    Get a template by difficulty level.
    
    Args:
        difficulty: "easy", "medium", "hard", or "adversarial"
    
    Returns:
        A template string
    """
    if difficulty == "easy":
        # Clean, canonical templates
        from .templates import ALL_SINGLE_ENTITY_TEMPLATES
        return random.choice(ALL_SINGLE_ENTITY_TEMPLATES)
    
    elif difficulty == "medium":
        # Mix of clean and informal
        templates = INFORMAL_TEMPLATES + OCR_ARTIFACT_TEMPLATES
        return random.choice(templates)
    
    elif difficulty == "hard":
        # Ambiguous and noisy
        templates = AMBIGUOUS_POSITIVE_TEMPLATES + HINGLISH_TEMPLATES
        return random.choice(templates)
    
    elif difficulty == "adversarial":
        # Evasion attempts
        return random.choice(EVASION_TEMPLATES)
    
    else:
        return random.choice(ALL_ADVERSARIAL_TEMPLATES)

