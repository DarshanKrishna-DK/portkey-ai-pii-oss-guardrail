"""
PII Data Augmentation and Noise Generation

Generates realistic, messy, and adversarial PII examples for robust model training.
Includes typos, OCR errors, obfuscation, partial masking, and evasion patterns.
"""

import random
import string
import re
from typing import List, Tuple, Optional, Callable
from enum import Enum
from dataclasses import dataclass


class NoiseLevel(Enum):
    """Noise intensity levels for augmentation."""
    NONE = 0        # Clean, canonical
    LIGHT = 1       # Minor typos, formatting variations
    MEDIUM = 2      # OCR-like errors, mixed separators
    HEAVY = 3       # Significant corruption, partial masking
    ADVERSARIAL = 4 # Deliberate evasion attempts


class ConfidenceLevel(Enum):
    """Detection confidence levels for training labels."""
    HIGH = 0.95      # Clear, unambiguous PII
    MEDIUM = 0.75    # Likely PII with some noise
    LOW = 0.55       # Ambiguous, could be PII
    UNCERTAIN = 0.35 # Very unclear, borderline


@dataclass
class AugmentedValue:
    """An augmented PII value with metadata."""
    original: str
    augmented: str
    noise_level: NoiseLevel
    confidence: float
    augmentation_type: str
    is_valid_pii: bool = True  # False for dangerous negatives


# ============================================================================
# Character Confusion Maps (OCR-style errors, visual similarity)
# ============================================================================

CHAR_CONFUSION = {
    # Digit-letter confusion
    '0': ['O', 'o', 'Q', 'D'],
    '1': ['I', 'i', 'l', '|', 'L'],
    '2': ['Z', 'z'],
    '3': ['E', 'B'],
    '4': ['A', 'H'],
    '5': ['S', 's', '$'],
    '6': ['G', 'b'],
    '7': ['T', 'Y', '/'],
    '8': ['B', '&'],
    '9': ['g', 'q', 'P'],
    
    # Letter-digit confusion (reverse)
    'O': ['0'],
    'o': ['0'],
    'I': ['1', 'l', '|'],
    'i': ['1', 'l'],
    'l': ['1', 'I', '|'],
    'L': ['1'],
    'S': ['5', '$'],
    's': ['5'],
    'B': ['8', '3'],
    'G': ['6'],
    'Z': ['2'],
    'z': ['2'],
    
    # Similar-looking letters
    'a': ['@', 'α'],
    'A': ['4', '@'],
    'e': ['3', 'є'],
    'E': ['3'],
    't': ['+', '7'],
    'T': ['7', '+'],
}

# Keyboard proximity errors (QWERTY)
KEYBOARD_ADJACENT = {
    'q': ['w', 'a', '1', '2'],
    'w': ['q', 'e', 's', 'a', '2', '3'],
    'e': ['w', 'r', 'd', 's', '3', '4'],
    'r': ['e', 't', 'f', 'd', '4', '5'],
    't': ['r', 'y', 'g', 'f', '5', '6'],
    'y': ['t', 'u', 'h', 'g', '6', '7'],
    'u': ['y', 'i', 'j', 'h', '7', '8'],
    'i': ['u', 'o', 'k', 'j', '8', '9'],
    'o': ['i', 'p', 'l', 'k', '9', '0'],
    'p': ['o', 'l', '0'],
    'a': ['q', 'w', 's', 'z'],
    's': ['a', 'w', 'e', 'd', 'z', 'x'],
    'd': ['s', 'e', 'r', 'f', 'x', 'c'],
    'f': ['d', 'r', 't', 'g', 'c', 'v'],
    'g': ['f', 't', 'y', 'h', 'v', 'b'],
    'h': ['g', 'y', 'u', 'j', 'b', 'n'],
    'j': ['h', 'u', 'i', 'k', 'n', 'm'],
    'k': ['j', 'i', 'o', 'l', 'm'],
    'l': ['k', 'o', 'p'],
    'z': ['a', 's', 'x'],
    'x': ['z', 's', 'd', 'c'],
    'c': ['x', 'd', 'f', 'v'],
    'v': ['c', 'f', 'g', 'b'],
    'b': ['v', 'g', 'h', 'n'],
    'n': ['b', 'h', 'j', 'm'],
    'm': ['n', 'j', 'k'],
    '1': ['2', 'q'],
    '2': ['1', '3', 'q', 'w'],
    '3': ['2', '4', 'w', 'e'],
    '4': ['3', '5', 'e', 'r'],
    '5': ['4', '6', 'r', 't'],
    '6': ['5', '7', 't', 'y'],
    '7': ['6', '8', 'y', 'u'],
    '8': ['7', '9', 'u', 'i'],
    '9': ['8', '0', 'i', 'o'],
    '0': ['9', 'o', 'p'],
}


# ============================================================================
# Noise Generators
# ============================================================================

def apply_ocr_noise(text: str, intensity: float = 0.1) -> str:
    """Apply OCR-style character confusion."""
    result = []
    for char in text:
        if random.random() < intensity and char in CHAR_CONFUSION:
            result.append(random.choice(CHAR_CONFUSION[char]))
        else:
            result.append(char)
    return ''.join(result)


def apply_typo(text: str, intensity: float = 0.1) -> str:
    """Apply realistic typos (transposition, deletion, insertion, substitution)."""
    if len(text) < 2:
        return text
    
    result = list(text)
    num_errors = max(1, int(len(text) * intensity))
    
    for _ in range(num_errors):
        if not result:
            break
            
        error_type = random.choice(['transpose', 'delete', 'insert', 'substitute', 'double'])
        pos = random.randint(0, len(result) - 1)
        
        if error_type == 'transpose' and pos < len(result) - 1:
            # Swap adjacent characters
            result[pos], result[pos + 1] = result[pos + 1], result[pos]
        
        elif error_type == 'delete' and len(result) > 1:
            # Delete a character
            result.pop(pos)
        
        elif error_type == 'insert':
            # Insert a random character or duplicate
            if random.random() < 0.5 and pos > 0:
                result.insert(pos, result[pos - 1])  # Duplicate previous
            else:
                char = result[pos].lower()
                if char in KEYBOARD_ADJACENT:
                    result.insert(pos, random.choice(KEYBOARD_ADJACENT[char]))
        
        elif error_type == 'substitute':
            # Substitute with keyboard-adjacent character
            char = result[pos].lower()
            if char in KEYBOARD_ADJACENT:
                result[pos] = random.choice(KEYBOARD_ADJACENT[char])
        
        elif error_type == 'double':
            # Double a character (common typo)
            result.insert(pos, result[pos])
    
    return ''.join(result)


def apply_separator_noise(text: str, original_sep: str = ' ') -> str:
    """Apply random separator variations."""
    separators = [' ', '-', '.', '/', '_', '  ', ' - ', '']
    new_sep = random.choice(separators)
    return text.replace(original_sep, new_sep)


def apply_case_noise(text: str) -> str:
    """Apply random case changes."""
    case_type = random.choice(['upper', 'lower', 'random', 'original'])
    
    if case_type == 'upper':
        return text.upper()
    elif case_type == 'lower':
        return text.lower()
    elif case_type == 'random':
        return ''.join(c.upper() if random.random() < 0.5 else c.lower() for c in text)
    return text


# ============================================================================
# PII-Specific Augmenters
# ============================================================================

class AadhaarAugmenter:
    """Augmentation strategies for Aadhaar numbers."""
    
    @staticmethod
    def clean(aadhaar: str) -> AugmentedValue:
        """Return clean, canonical format."""
        digits = re.sub(r'\D', '', aadhaar)
        formatted = f"{digits[:4]} {digits[4:8]} {digits[8:12]}"
        return AugmentedValue(
            original=aadhaar,
            augmented=formatted,
            noise_level=NoiseLevel.NONE,
            confidence=0.95,
            augmentation_type="clean"
        )
    
    @staticmethod
    def no_spaces(aadhaar: str) -> AugmentedValue:
        """Remove all spaces."""
        digits = re.sub(r'\D', '', aadhaar)
        return AugmentedValue(
            original=aadhaar,
            augmented=digits,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.90,
            augmentation_type="no_spaces"
        )
    
    @staticmethod
    def dashed(aadhaar: str) -> AugmentedValue:
        """Use dashes instead of spaces."""
        digits = re.sub(r'\D', '', aadhaar)
        formatted = f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}"
        return AugmentedValue(
            original=aadhaar,
            augmented=formatted,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.90,
            augmentation_type="dashed"
        )
    
    @staticmethod
    def mixed_separators(aadhaar: str) -> AugmentedValue:
        """Use mixed separators."""
        digits = re.sub(r'\D', '', aadhaar)
        sep1 = random.choice([' ', '-', '.', '/'])
        sep2 = random.choice([' ', '-', '.', '/'])
        formatted = f"{digits[:4]}{sep1}{digits[4:8]}{sep2}{digits[8:12]}"
        return AugmentedValue(
            original=aadhaar,
            augmented=formatted,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.80,
            augmentation_type="mixed_separators"
        )
    
    @staticmethod
    def ocr_corrupted(aadhaar: str) -> AugmentedValue:
        """Apply OCR-style corruption."""
        digits = re.sub(r'\D', '', aadhaar)
        corrupted = apply_ocr_noise(digits, intensity=0.15)
        formatted = f"{corrupted[:4]} {corrupted[4:8]} {corrupted[8:12]}"
        return AugmentedValue(
            original=aadhaar,
            augmented=formatted,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.70,
            augmentation_type="ocr_corrupted"
        )
    
    @staticmethod
    def typo(aadhaar: str) -> AugmentedValue:
        """Apply typo errors."""
        digits = re.sub(r'\D', '', aadhaar)
        typo_digits = apply_typo(digits, intensity=0.1)
        # Ensure we still have ~12 chars
        typo_digits = typo_digits[:14]  # Allow some extra
        formatted = f"{typo_digits[:4]} {typo_digits[4:8]} {typo_digits[8:12]}" if len(typo_digits) >= 12 else typo_digits
        return AugmentedValue(
            original=aadhaar,
            augmented=formatted,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.65,
            augmentation_type="typo"
        )
    
    @staticmethod
    def partial_masked(aadhaar: str) -> AugmentedValue:
        """Partially mask the Aadhaar (common in real-world usage)."""
        digits = re.sub(r'\D', '', aadhaar)
        mask_type = random.choice(['last4', 'first8_masked', 'middle_masked'])
        
        if mask_type == 'last4':
            masked = f"XXXX XXXX {digits[8:12]}"
        elif mask_type == 'first8_masked':
            masked = f"****-****-{digits[8:12]}"
        else:
            masked = f"{digits[:4]}-XXXX-{digits[8:12]}"
        
        return AugmentedValue(
            original=aadhaar,
            augmented=masked,
            noise_level=NoiseLevel.HEAVY,
            confidence=0.60,
            augmentation_type="partial_masked"
        )
    
    @staticmethod
    def written_out(aadhaar: str) -> AugmentedValue:
        """Write digits as words (evasion attempt)."""
        digit_words = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        digits = re.sub(r'\D', '', aadhaar)
        # Only write out a few digits to make it harder
        written = []
        for i, d in enumerate(digits):
            if random.random() < 0.3:  # 30% chance to write out
                written.append(digit_words[d])
            else:
                written.append(d)
        return AugmentedValue(
            original=aadhaar,
            augmented=' '.join(written),
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.50,
            augmentation_type="written_out"
        )
    
    @staticmethod
    def spaced_out(aadhaar: str) -> AugmentedValue:
        """Add spaces between each digit (evasion)."""
        digits = re.sub(r'\D', '', aadhaar)
        spaced = ' '.join(digits)
        return AugmentedValue(
            original=aadhaar,
            augmented=spaced,
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.55,
            augmentation_type="spaced_out"
        )
    
    @staticmethod
    def truncated(aadhaar: str) -> AugmentedValue:
        """Truncate to partial number."""
        digits = re.sub(r'\D', '', aadhaar)
        trunc_type = random.choice(['first6', 'last6', 'last4', 'first8'])
        
        if trunc_type == 'first6':
            truncated = digits[:6]
        elif trunc_type == 'last6':
            truncated = digits[6:]
        elif trunc_type == 'last4':
            truncated = digits[8:]
        else:
            truncated = digits[:8]
        
        return AugmentedValue(
            original=aadhaar,
            augmented=truncated,
            noise_level=NoiseLevel.HEAVY,
            confidence=0.45,
            augmentation_type="truncated"
        )


class PANAugmenter:
    """Augmentation strategies for PAN numbers."""
    
    @staticmethod
    def clean(pan: str) -> AugmentedValue:
        """Return clean, uppercase format."""
        return AugmentedValue(
            original=pan,
            augmented=pan.upper(),
            noise_level=NoiseLevel.NONE,
            confidence=0.95,
            augmentation_type="clean"
        )
    
    @staticmethod
    def lowercase(pan: str) -> AugmentedValue:
        """Return lowercase."""
        return AugmentedValue(
            original=pan,
            augmented=pan.lower(),
            noise_level=NoiseLevel.LIGHT,
            confidence=0.90,
            augmentation_type="lowercase"
        )
    
    @staticmethod
    def mixed_case(pan: str) -> AugmentedValue:
        """Random case mixing."""
        mixed = ''.join(c.upper() if random.random() < 0.5 else c.lower() for c in pan)
        return AugmentedValue(
            original=pan,
            augmented=mixed,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.80,
            augmentation_type="mixed_case"
        )
    
    @staticmethod
    def ocr_corrupted(pan: str) -> AugmentedValue:
        """Apply OCR-style corruption."""
        corrupted = apply_ocr_noise(pan.upper(), intensity=0.2)
        return AugmentedValue(
            original=pan,
            augmented=corrupted,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.65,
            augmentation_type="ocr_corrupted"
        )
    
    @staticmethod
    def spaced(pan: str) -> AugmentedValue:
        """Add spaces between groups."""
        formatted = f"{pan[:5]} {pan[5:9]} {pan[9]}"
        return AugmentedValue(
            original=pan,
            augmented=formatted,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.85,
            augmentation_type="spaced"
        )
    
    @staticmethod
    def partial_masked(pan: str) -> AugmentedValue:
        """Partially mask PAN."""
        mask_type = random.choice(['last4', 'middle', 'first5'])
        
        if mask_type == 'last4':
            masked = f"{pan[:5]}XXXX{pan[9]}"
        elif mask_type == 'middle':
            masked = f"{pan[:3]}****{pan[7:]}"
        else:
            masked = f"XXXXX{pan[5:]}"
        
        return AugmentedValue(
            original=pan,
            augmented=masked,
            noise_level=NoiseLevel.HEAVY,
            confidence=0.55,
            augmentation_type="partial_masked"
        )
    
    @staticmethod
    def typo(pan: str) -> AugmentedValue:
        """Apply typo."""
        typo_pan = apply_typo(pan, intensity=0.1)
        return AugmentedValue(
            original=pan,
            augmented=typo_pan.upper(),
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.60,
            augmentation_type="typo"
        )


class EmailAugmenter:
    """Augmentation strategies for email addresses."""
    
    @staticmethod
    def clean(email: str) -> AugmentedValue:
        """Return clean format."""
        return AugmentedValue(
            original=email,
            augmented=email.lower(),
            noise_level=NoiseLevel.NONE,
            confidence=0.95,
            augmentation_type="clean"
        )
    
    @staticmethod
    def uppercase(email: str) -> AugmentedValue:
        """Uppercase email."""
        return AugmentedValue(
            original=email,
            augmented=email.upper(),
            noise_level=NoiseLevel.LIGHT,
            confidence=0.90,
            augmentation_type="uppercase"
        )
    
    @staticmethod
    def spaced_at(email: str) -> AugmentedValue:
        """Space around @."""
        spaced = email.replace('@', ' @ ')
        return AugmentedValue(
            original=email,
            augmented=spaced,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.75,
            augmentation_type="spaced_at"
        )
    
    @staticmethod
    def at_written(email: str) -> AugmentedValue:
        """Replace @ with 'at'."""
        written = email.replace('@', ' at ')
        return AugmentedValue(
            original=email,
            augmented=written,
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.60,
            augmentation_type="at_written"
        )
    
    @staticmethod
    def dot_written(email: str) -> AugmentedValue:
        """Replace . with 'dot'."""
        written = email.replace('.', ' dot ')
        return AugmentedValue(
            original=email,
            augmented=written,
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.55,
            augmentation_type="dot_written"
        )
    
    @staticmethod
    def obfuscated(email: str) -> AugmentedValue:
        """Full obfuscation: @ -> at, . -> dot."""
        obfuscated = email.replace('@', ' [at] ').replace('.', ' [dot] ')
        return AugmentedValue(
            original=email,
            augmented=obfuscated,
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.50,
            augmentation_type="obfuscated"
        )
    
    @staticmethod
    def typo(email: str) -> AugmentedValue:
        """Apply typo to local part."""
        parts = email.split('@')
        if len(parts) == 2:
            local = apply_typo(parts[0], intensity=0.15)
            typo_email = f"{local}@{parts[1]}"
        else:
            typo_email = apply_typo(email, intensity=0.1)
        return AugmentedValue(
            original=email,
            augmented=typo_email,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.70,
            augmentation_type="typo"
        )
    
    @staticmethod
    def partial_masked(email: str) -> AugmentedValue:
        """Partially mask email."""
        parts = email.split('@')
        if len(parts) == 2:
            local = parts[0]
            domain = parts[1]
            if len(local) > 2:
                masked = f"{local[0]}***{local[-1]}@{domain}"
            else:
                masked = f"***@{domain}"
        else:
            masked = "***@***.***"
        return AugmentedValue(
            original=email,
            augmented=masked,
            noise_level=NoiseLevel.HEAVY,
            confidence=0.50,
            augmentation_type="partial_masked"
        )


class PhoneAugmenter:
    """Augmentation strategies for phone numbers."""
    
    @staticmethod
    def clean_indian(phone: str) -> AugmentedValue:
        """Clean Indian format."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        formatted = f"+91 {digits[:5]} {digits[5:]}"
        return AugmentedValue(
            original=phone,
            augmented=formatted,
            noise_level=NoiseLevel.NONE,
            confidence=0.95,
            augmentation_type="clean_indian"
        )
    
    @staticmethod
    def no_country_code(phone: str) -> AugmentedValue:
        """Remove country code."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        return AugmentedValue(
            original=phone,
            augmented=digits,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.85,
            augmentation_type="no_country_code"
        )
    
    @staticmethod
    def dashed(phone: str) -> AugmentedValue:
        """Dashed format."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return AugmentedValue(
            original=phone,
            augmented=formatted,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.90,
            augmentation_type="dashed"
        )
    
    @staticmethod
    def parentheses(phone: str) -> AugmentedValue:
        """US-style parentheses."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        if len(digits) >= 10:
            formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"
        else:
            formatted = digits
        return AugmentedValue(
            original=phone,
            augmented=formatted,
            noise_level=NoiseLevel.LIGHT,
            confidence=0.85,
            augmentation_type="parentheses"
        )
    
    @staticmethod
    def spaced_out(phone: str) -> AugmentedValue:
        """Space between each digit."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        spaced = ' '.join(digits)
        return AugmentedValue(
            original=phone,
            augmented=spaced,
            noise_level=NoiseLevel.ADVERSARIAL,
            confidence=0.55,
            augmentation_type="spaced_out"
        )
    
    @staticmethod
    def partial_masked(phone: str) -> AugmentedValue:
        """Partially mask phone."""
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('91'):
            digits = digits[2:]
        masked = f"XXXXXX{digits[-4:]}"
        return AugmentedValue(
            original=phone,
            augmented=masked,
            noise_level=NoiseLevel.HEAVY,
            confidence=0.55,
            augmentation_type="partial_masked"
        )
    
    @staticmethod
    def ocr_corrupted(phone: str) -> AugmentedValue:
        """OCR corruption."""
        corrupted = apply_ocr_noise(phone, intensity=0.15)
        return AugmentedValue(
            original=phone,
            augmented=corrupted,
            noise_level=NoiseLevel.MEDIUM,
            confidence=0.65,
            augmentation_type="ocr_corrupted"
        )


# ============================================================================
# Dangerous Negative Generators (False Positive Traps)
# ============================================================================

class DangerousNegativeGenerator:
    """Generate PII-like strings that should NOT be flagged."""
    
    @staticmethod
    def aadhaar_like_order_id() -> Tuple[str, str]:
        """Generate 12-digit order/reference IDs."""
        templates = [
            "Order ID: {id}",
            "Reference number {id}",
            "Transaction #{id}",
            "Booking ID: {id}",
            "Invoice number: {id}",
            "Ticket ID {id}",
            "Confirmation: {id}",
        ]
        # Generate 12 digits that look like Aadhaar but aren't
        # Start with 0 or 1 (invalid for Aadhaar)
        id_num = random.choice(['0', '1']) + ''.join(random.choices(string.digits, k=11))
        formatted = f"{id_num[:4]} {id_num[4:8]} {id_num[8:]}"
        template = random.choice(templates)
        return template.format(id=formatted), "NOT_PII"
    
    @staticmethod
    def pan_like_product_code() -> Tuple[str, str]:
        """Generate PAN-like product/serial codes."""
        templates = [
            "Product code: {code}",
            "SKU: {code}",
            "Model number {code}",
            "Part ID: {code}",
            "Serial: {code}",
            "Item code {code}",
        ]
        # Generate codes that look like PAN but have invalid 4th char
        letters1 = ''.join(random.choices(string.ascii_uppercase, k=3))
        invalid_4th = random.choice(['D', 'E', 'I', 'M', 'N', 'O', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z'])
        letter5 = random.choice(string.ascii_uppercase)
        digits = ''.join(random.choices(string.digits, k=4))
        last = random.choice(string.ascii_uppercase)
        code = f"{letters1}{invalid_4th}{letter5}{digits}{last}"
        template = random.choice(templates)
        return template.format(code=code), "NOT_PII"
    
    @staticmethod
    def phone_like_id() -> Tuple[str, str]:
        """Generate phone-like IDs that aren't phones."""
        templates = [
            "Account: {num}",
            "Member ID: {num}",
            "Policy number: {num}",
            "Registration: {num}",
            "License plate: {num}",
        ]
        # 10 digits starting with 0-5 (not valid Indian mobile)
        first = random.choice(['0', '1', '2', '3', '4', '5'])
        rest = ''.join(random.choices(string.digits, k=9))
        num = first + rest
        template = random.choice(templates)
        return template.format(num=num), "NOT_PII"
    
    @staticmethod
    def email_like_text() -> Tuple[str, str]:
        """Generate email-like strings that aren't emails."""
        templates = [
            "Use user@domain format for login",
            "Pattern: name@company",
            "Example: test@example",
            "Format should be x@y.z",
            "The placeholder is user@host.tld",
        ]
        return random.choice(templates), "NOT_PII"
    
    @staticmethod
    def ssn_like_number() -> Tuple[str, str]:
        """Generate SSN-like numbers that aren't SSNs."""
        templates = [
            "Part number: {num}",
            "Version {num}",
            "Code: {num}",
            "Format: {num}",
            "ID scheme: {num}",
        ]
        # Invalid SSN patterns (area 000, 666, 900+)
        invalid_area = random.choice(['000', '666', str(random.randint(900, 999))])
        group = f"{random.randint(0, 99):02d}"
        serial = f"{random.randint(0, 9999):04d}"
        num = f"{invalid_area}-{group}-{serial}"
        template = random.choice(templates)
        return template.format(num=num), "NOT_PII"
    
    @staticmethod
    def date_like_number() -> Tuple[str, str]:
        """Generate date-formatted numbers."""
        templates = [
            "Date: {date}",
            "Deadline: {date}",
            "Scheduled for {date}",
            "Due by {date}",
            "Expires: {date}",
        ]
        # Date formats that might look like PII
        formats = [
            f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(1990,2025)}",
            f"{random.randint(1,12):02d}/{random.randint(1,28):02d}/{random.randint(20,25)}",
            f"{random.randint(2020,2025)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        ]
        date = random.choice(formats)
        template = random.choice(templates)
        return template.format(date=date), "NOT_PII"
    
    @staticmethod
    def ip_address() -> Tuple[str, str]:
        """Generate IP addresses (not PII in our context)."""
        templates = [
            "Server IP: {ip}",
            "Connect to {ip}",
            "Host: {ip}",
            "Gateway: {ip}",
        ]
        ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"
        template = random.choice(templates)
        return template.format(ip=ip), "NOT_PII"
    
    @staticmethod
    def alphanumeric_code() -> Tuple[str, str]:
        """Generate random alphanumeric codes."""
        templates = [
            "Promo code: {code}",
            "Coupon: {code}",
            "Voucher {code}",
            "Discount code: {code}",
            "Access code: {code}",
            "PIN: {code}",
        ]
        length = random.randint(6, 12)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        template = random.choice(templates)
        return template.format(code=code), "NOT_PII"


# ============================================================================
# Augmentation Registry
# ============================================================================

AUGMENTERS = {
    "IN_AADHAAR": [
        (AadhaarAugmenter.clean, 0.15),
        (AadhaarAugmenter.no_spaces, 0.10),
        (AadhaarAugmenter.dashed, 0.10),
        (AadhaarAugmenter.mixed_separators, 0.10),
        (AadhaarAugmenter.ocr_corrupted, 0.10),
        (AadhaarAugmenter.typo, 0.10),
        (AadhaarAugmenter.partial_masked, 0.10),
        (AadhaarAugmenter.written_out, 0.05),
        (AadhaarAugmenter.spaced_out, 0.10),
        (AadhaarAugmenter.truncated, 0.10),
    ],
    "IN_PAN": [
        (PANAugmenter.clean, 0.20),
        (PANAugmenter.lowercase, 0.15),
        (PANAugmenter.mixed_case, 0.15),
        (PANAugmenter.ocr_corrupted, 0.15),
        (PANAugmenter.spaced, 0.10),
        (PANAugmenter.partial_masked, 0.15),
        (PANAugmenter.typo, 0.10),
    ],
    "EMAIL_ADDRESS": [
        (EmailAugmenter.clean, 0.20),
        (EmailAugmenter.uppercase, 0.10),
        (EmailAugmenter.spaced_at, 0.10),
        (EmailAugmenter.at_written, 0.15),
        (EmailAugmenter.dot_written, 0.10),
        (EmailAugmenter.obfuscated, 0.10),
        (EmailAugmenter.typo, 0.15),
        (EmailAugmenter.partial_masked, 0.10),
    ],
    "PHONE_NUMBER": [
        (PhoneAugmenter.clean_indian, 0.15),
        (PhoneAugmenter.no_country_code, 0.15),
        (PhoneAugmenter.dashed, 0.15),
        (PhoneAugmenter.parentheses, 0.10),
        (PhoneAugmenter.spaced_out, 0.10),
        (PhoneAugmenter.partial_masked, 0.15),
        (PhoneAugmenter.ocr_corrupted, 0.20),
    ],
}

DANGEROUS_NEGATIVE_GENERATORS = [
    (DangerousNegativeGenerator.aadhaar_like_order_id, 0.20),
    (DangerousNegativeGenerator.pan_like_product_code, 0.15),
    (DangerousNegativeGenerator.phone_like_id, 0.15),
    (DangerousNegativeGenerator.email_like_text, 0.10),
    (DangerousNegativeGenerator.ssn_like_number, 0.10),
    (DangerousNegativeGenerator.date_like_number, 0.10),
    (DangerousNegativeGenerator.ip_address, 0.10),
    (DangerousNegativeGenerator.alphanumeric_code, 0.10),
]


def augment_pii_value(entity_type: str, value: str) -> AugmentedValue:
    """
    Apply a random augmentation to a PII value based on entity type.
    
    Uses weighted random selection to ensure diverse augmentation distribution.
    """
    if entity_type not in AUGMENTERS:
        return AugmentedValue(
            original=value,
            augmented=value,
            noise_level=NoiseLevel.NONE,
            confidence=0.95,
            augmentation_type="passthrough"
        )
    
    augmenters = AUGMENTERS[entity_type]
    weights = [w for _, w in augmenters]
    funcs = [f for f, _ in augmenters]
    
    selected_func = random.choices(funcs, weights=weights, k=1)[0]
    return selected_func(value)


def generate_dangerous_negative() -> Tuple[str, str]:
    """
    Generate a dangerous negative sample (looks like PII but isn't).
    
    Returns:
        Tuple of (text, label) where label is "NOT_PII"
    """
    weights = [w for _, w in DANGEROUS_NEGATIVE_GENERATORS]
    funcs = [f for f, _ in DANGEROUS_NEGATIVE_GENERATORS]
    
    selected_func = random.choices(funcs, weights=weights, k=1)[0]
    return selected_func()

