"""
Entity Configuration for PII Detection

Defines entity types, regex patterns, context words, severity scores,
and synthetic data generators aligned with Microsoft Presidio naming conventions.
"""

import random
import string
from typing import Callable, Dict, List, Any


def generate_aadhaar() -> str:
    """Generate a valid-format Aadhaar number (12 digits with spaces)."""
    # Aadhaar format: XXXX XXXX XXXX (12 digits)
    # First digit cannot be 0 or 1
    first_digit = str(random.randint(2, 9))
    remaining = ''.join(random.choices(string.digits, k=11))
    aadhaar = first_digit + remaining
    return f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}"


def generate_aadhaar_no_space() -> str:
    """Generate Aadhaar without spaces."""
    first_digit = str(random.randint(2, 9))
    remaining = ''.join(random.choices(string.digits, k=11))
    return first_digit + remaining


def generate_pan() -> str:
    """
    Generate a valid-format PAN number.
    Format: AAAAA0000A (5 letters + 4 digits + 1 letter)
    - First 3 letters: Random (AAA to ZZZ)
    - 4th letter: Entity type (P=Person, C=Company, H=HUF, etc.)
    - 5th letter: First letter of surname
    - 4 digits: Sequential number
    - Last letter: Alphabetic check digit
    """
    first_three = ''.join(random.choices(string.ascii_uppercase, k=3))
    entity_type = random.choice(['P', 'C', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G'])
    surname_letter = random.choice(string.ascii_uppercase)
    digits = ''.join(random.choices(string.digits, k=4))
    check_letter = random.choice(string.ascii_uppercase)
    return f"{first_three}{entity_type}{surname_letter}{digits}{check_letter}"


def generate_email() -> str:
    """Generate a realistic email address."""
    first_names = ['rahul', 'priya', 'amit', 'neha', 'vijay', 'sunita', 'raj', 'anita', 
                   'kumar', 'deepa', 'john', 'sarah', 'mike', 'lisa', 'david']
    last_names = ['sharma', 'patel', 'singh', 'kumar', 'gupta', 'verma', 'joshi', 
                  'reddy', 'nair', 'iyer', 'smith', 'johnson', 'williams', 'brown']
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 
               'company.com', 'work.org', 'mail.in', 'email.co.in']
    
    first = random.choice(first_names)
    last = random.choice(last_names)
    domain = random.choice(domains)
    
    patterns = [
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
        f"{first}_{last}@{domain}",
        f"{first}.{last}{random.randint(1, 99)}@{domain}",
        f"{first[0]}{last}@{domain}",
    ]
    return random.choice(patterns)


def generate_phone_indian() -> str:
    """Generate an Indian phone number."""
    # Indian mobile numbers start with 6, 7, 8, or 9
    first_digit = random.choice(['6', '7', '8', '9'])
    remaining = ''.join(random.choices(string.digits, k=9))
    number = first_digit + remaining
    
    formats = [
        f"+91 {number[:5]} {number[5:]}",
        f"+91-{number}",
        f"91{number}",
        f"{number[:5]}-{number[5:]}",
        number,
    ]
    return random.choice(formats)


def generate_phone_us() -> str:
    """Generate a US phone number."""
    area_code = ''.join(random.choices(string.digits, k=3))
    exchange = ''.join(random.choices(string.digits, k=3))
    subscriber = ''.join(random.choices(string.digits, k=4))
    
    formats = [
        f"({area_code}) {exchange}-{subscriber}",
        f"{area_code}-{exchange}-{subscriber}",
        f"+1 {area_code} {exchange} {subscriber}",
        f"1-{area_code}-{exchange}-{subscriber}",
    ]
    return random.choice(formats)


def generate_person_name() -> str:
    """Generate a realistic person name."""
    indian_first = ['Rahul', 'Priya', 'Amit', 'Neha', 'Vijay', 'Sunita', 'Raj', 
                    'Anita', 'Deepak', 'Kavita', 'Suresh', 'Meena', 'Arun', 'Pooja',
                    'Darshan', 'Krishna', 'Lakshmi', 'Ganesh', 'Sita', 'Ram']
    indian_last = ['Sharma', 'Patel', 'Singh', 'Kumar', 'Gupta', 'Verma', 'Joshi',
                   'Reddy', 'Nair', 'Iyer', 'Rao', 'Mehta', 'Shah', 'Das', 'Pillai']
    western_first = ['John', 'Sarah', 'Michael', 'Emily', 'David', 'Jessica', 
                     'Robert', 'Jennifer', 'William', 'Amanda', 'James', 'Ashley']
    western_last = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                    'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Wilson', 'Taylor']
    
    if random.random() < 0.7:  # 70% Indian names
        first = random.choice(indian_first)
        last = random.choice(indian_last)
    else:
        first = random.choice(western_first)
        last = random.choice(western_last)
    
    return f"{first} {last}"


def generate_ssn() -> str:
    """Generate a US Social Security Number."""
    # SSN format: XXX-XX-XXXX
    # Area number (first 3): 001-899 (excluding 666)
    area = random.randint(1, 899)
    while area == 666:
        area = random.randint(1, 899)
    group = random.randint(1, 99)
    serial = random.randint(1, 9999)
    return f"{area:03d}-{group:02d}-{serial:04d}"


def generate_credit_card() -> str:
    """Generate a credit card number (Luhn-valid format)."""
    # Generate a 15-digit number and calculate Luhn check digit
    prefix = random.choice(['4', '5', '37', '6011'])  # Visa, MC, Amex, Discover
    
    if prefix == '37':  # Amex is 15 digits
        remaining_length = 13
    else:
        remaining_length = 15
    
    number = prefix + ''.join(random.choices(string.digits, k=remaining_length - len(prefix)))
    
    # Calculate Luhn check digit
    def luhn_checksum(card_number: str) -> int:
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        return checksum % 10
    
    check_digit = (10 - luhn_checksum(number + '0')) % 10
    card = number + str(check_digit)
    
    # Format with spaces
    if prefix == '37':
        return f"{card[:4]} {card[4:10]} {card[10:]}"
    else:
        return f"{card[:4]} {card[4:8]} {card[8:12]} {card[12:]}"


# Severity scores for each entity type (1-10 scale)
SEVERITY_SCORES: Dict[str, int] = {
    "IN_AADHAAR": 10,      # Critical - National ID
    "IN_PAN": 9,           # Critical - Tax ID
    "US_SSN": 10,          # Critical - Social Security
    "CREDIT_CARD": 9,      # Critical - Financial
    "EMAIL_ADDRESS": 3,    # Low - Contact info
    "PHONE_NUMBER": 3,     # Low - Contact info
    "PERSON": 2,           # Low - Name only
    "LOCATION": 2,         # Low - General location
    "DATE_TIME": 1,        # Minimal - Temporal info
    "IP_ADDRESS": 4,       # Medium - Network identifier
    "URL": 2,              # Low - Web address
}


# Main entity configuration
ENTITY_CONFIG: Dict[str, Dict[str, Any]] = {
    "IN_AADHAAR": {
        "description": "Indian Aadhaar Number (12-digit unique ID)",
        "pattern": r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
        "context_words": [
            "aadhaar", "aadhar", "uidai", "uid", "unique identification",
            "unique id", "aadhaar number", "aadhaar card", "aadhaar no",
            "my aadhaar", "aadhaar is", "aadhaar:", "uid number"
        ],
        "severity": 10,
        "generator": generate_aadhaar,
        "generator_no_space": generate_aadhaar_no_space,
        "examples": ["2345 6789 0123", "987654321098"],
    },
    
    "IN_PAN": {
        "description": "Indian Permanent Account Number (Tax ID)",
        "pattern": r"\b[A-Z]{3}[ABCFGHLJPTK][A-Z]\d{4}[A-Z]\b",
        "context_words": [
            "pan", "pan card", "pan number", "permanent account number",
            "tax id", "income tax", "pan no", "my pan", "pan is", "pan:",
            "taxpayer", "tax identification"
        ],
        "severity": 9,
        "generator": generate_pan,
        "examples": ["ABCPD1234E", "BNZPM2501F"],
    },
    
    "EMAIL_ADDRESS": {
        "description": "Email Address",
        "pattern": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "context_words": [
            "email", "e-mail", "mail", "contact", "reach me at",
            "email address", "email id", "mail id", "send to",
            "write to", "email:", "mail:"
        ],
        "severity": 3,
        "generator": generate_email,
        "examples": ["user@example.com", "john.doe@company.org"],
    },
    
    "PHONE_NUMBER": {
        "description": "Phone Number (Indian or US format)",
        "pattern": r"(?:\+?91[-\s]?)?[6-9]\d{9}|(?:\+?1[-\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        "context_words": [
            "phone", "mobile", "cell", "call", "contact number",
            "phone number", "mobile number", "telephone", "tel",
            "reach me", "call me", "phone:", "mobile:"
        ],
        "severity": 3,
        "generator": generate_phone_indian,
        "generator_us": generate_phone_us,
        "examples": ["+91 98765 43210", "(555) 123-4567"],
    },
    
    "PERSON": {
        "description": "Person Name",
        "pattern": r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
        "context_words": [
            "name", "called", "mr", "ms", "mrs", "dr", "prof",
            "my name", "name is", "i am", "this is", "named",
            "name:", "person", "individual"
        ],
        "severity": 2,
        "generator": generate_person_name,
        "examples": ["Rahul Sharma", "John Smith"],
    },
    
    "US_SSN": {
        "description": "US Social Security Number",
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "context_words": [
            "ssn", "social security", "social security number",
            "ss number", "ssn:", "social security:"
        ],
        "severity": 10,
        "generator": generate_ssn,
        "examples": ["123-45-6789", "987-65-4321"],
    },
    
    "CREDIT_CARD": {
        "description": "Credit/Debit Card Number",
        "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b",
        "context_words": [
            "card", "credit card", "debit card", "card number",
            "cc", "visa", "mastercard", "amex", "credit", "debit",
            "card no", "card:", "payment card"
        ],
        "severity": 9,
        "generator": generate_credit_card,
        "examples": ["4532 1234 5678 9012", "3782 822463 10005"],
    },
}


# BIO tag labels for NER
BIO_LABELS: List[str] = [
    "O",  # Outside any entity
    "B-IN_AADHAAR", "I-IN_AADHAAR",
    "B-IN_PAN", "I-IN_PAN", 
    "B-EMAIL_ADDRESS", "I-EMAIL_ADDRESS",
    "B-PHONE_NUMBER", "I-PHONE_NUMBER",
    "B-PERSON", "I-PERSON",
    "B-US_SSN", "I-US_SSN",
    "B-CREDIT_CARD", "I-CREDIT_CARD",
    "B-LOCATION", "I-LOCATION",
]


def get_all_context_words() -> Dict[str, List[str]]:
    """Get all context words for all entity types."""
    return {
        entity_type: config["context_words"] 
        for entity_type, config in ENTITY_CONFIG.items()
    }


def get_generator(entity_type: str) -> Callable[[], str]:
    """Get the generator function for an entity type."""
    if entity_type not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity type: {entity_type}")
    return ENTITY_CONFIG[entity_type]["generator"]


def get_severity(entity_type: str) -> int:
    """Get severity score for an entity type."""
    return SEVERITY_SCORES.get(entity_type, 5)

