#!/usr/bin/env python3
"""
PII Guardrail Training Data Generator v2

CRITICAL FIXES from v1:
1. Output format: flag (0/1), confidence (1-10) - Presidio aligned
2. 50% negative samples to prevent false positives
3. Entities MUST exist in text at exact positions
4. No hallucination - only flag what's actually there

Run this script to generate train_v2.jsonl and eval_v2.jsonl
Upload these files to Google Drive for training.
"""

import json
import random
import string
import os
from typing import List, Dict, Tuple

random.seed(42)

# ============================================================================
# SYSTEM PROMPT - Critical for model behavior
# ============================================================================
SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection system.

TASK: Analyze the input text and detect any PII entities.

OUTPUT FORMAT (strict JSON):
{
  "flagged": true or false, // true if PII found, false if no PII
  "confidence": 1-10,       // 10=certain, 1=very uncertain
  "entities": [             // Empty array if no PII
    {
      "type": "ENTITY_TYPE",
      "value": "exact text from input",
      "start": start_index,
      "end": end_index
    }
  ],
  "reason": "explanation"
}

ENTITY TYPES:
- IN_AADHAAR: Indian Aadhaar (12 digits, starts with 2-9)
- IN_PAN: Indian PAN (format: ABCDE1234F, 4th char is entity type)
- EMAIL_ADDRESS: Email addresses
- PHONE_NUMBER: Phone numbers (Indian: starts with 6-9)
- PERSON: Person names
- US_SSN: US Social Security (XXX-XX-XXXX, area not 000/666/900+)
- CREDIT_CARD: Credit card numbers (16 digits)

CRITICAL RULES:
1. ONLY flag text that ACTUALLY appears in the input
2. The "value" field MUST be an exact substring of the input
3. start/end positions MUST be accurate
4. If NO PII exists, return flagged=false with empty entities array
5. Do NOT hallucinate or invent PII that isn't there
6. Order IDs, product codes, dates, IP addresses are NOT PII

CONFIDENCE SCORING:
- 10: Perfect pattern match with strong context words
- 8-9: Strong match with some context
- 6-7: Pattern match without strong context
- 4-5: Weak pattern, ambiguous
- 1-3: Very uncertain, likely false positive"""


# ============================================================================
# PII Generators (valid formats only)
# ============================================================================
def gen_aadhaar() -> str:
    """Generate valid Aadhaar: 12 digits starting with 2-9."""
    first = str(random.randint(2, 9))
    rest = ''.join(random.choices(string.digits, k=11))
    num = first + rest
    return f"{num[:4]} {num[4:8]} {num[8:12]}"


def gen_pan() -> str:
    """Generate valid PAN: 5 letters + 4 digits + 1 letter."""
    first3 = ''.join(random.choices(string.ascii_uppercase, k=3))
    # 4th char must be valid entity type
    fourth = random.choice(['P', 'C', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G'])
    fifth = random.choice(string.ascii_uppercase)
    digits = ''.join(random.choices(string.digits, k=4))
    last = random.choice(string.ascii_uppercase)
    return f"{first3}{fourth}{fifth}{digits}{last}"


def gen_email() -> str:
    """Generate realistic email."""
    names = ['rahul', 'priya', 'amit', 'neha', 'john', 'sarah', 'mike', 'lisa']
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'company.in', 'work.org']
    return f"{random.choice(names)}{random.randint(1, 99)}@{random.choice(domains)}"


def gen_phone() -> str:
    """Generate valid Indian phone number."""
    first = random.choice(['6', '7', '8', '9'])
    rest = ''.join(random.choices(string.digits, k=9))
    return f"+91 {first}{rest[:4]} {rest[4:]}"


def gen_name() -> str:
    """Generate realistic person name."""
    first = random.choice(['Rahul', 'Priya', 'Amit', 'Neha', 'John', 'Sarah', 'Darshan', 'Krishna'])
    last = random.choice(['Sharma', 'Patel', 'Singh', 'Kumar', 'Smith', 'Johnson', 'Gupta', 'Reddy'])
    return f"{first} {last}"


def gen_ssn() -> str:
    """Generate valid US SSN format."""
    area = random.randint(100, 899)
    while area == 666:
        area = random.randint(100, 899)
    group = random.randint(10, 99)
    serial = random.randint(1000, 9999)
    return f"{area}-{group:02d}-{serial}"


def gen_cc() -> str:
    """Generate credit card number format."""
    prefix = random.choice(['4', '5'])  # Visa/Mastercard
    rest = ''.join(random.choices(string.digits, k=15))
    num = prefix + rest
    return f"{num[:4]} {num[4:8]} {num[8:12]} {num[12:16]}"


# ============================================================================
# Templates - POSITIVE (contains PII)
# ============================================================================
PII_TEMPLATES: List[Tuple[str, str, callable, int]] = [
    # Aadhaar - High confidence (context words)
    ("My Aadhaar number is {value}.", "IN_AADHAAR", gen_aadhaar, 10),
    ("Aadhaar: {value}", "IN_AADHAAR", gen_aadhaar, 10),
    ("UIDAI Aadhaar Card: {value}", "IN_AADHAAR", gen_aadhaar, 10),
    ("My UID is {value} for verification.", "IN_AADHAAR", gen_aadhaar, 9),
    ("Aadhaar no: {value}", "IN_AADHAAR", gen_aadhaar, 10),
    ("Please verify my Aadhaar {value}.", "IN_AADHAAR", gen_aadhaar, 10),
    ("Aadhaar card number: {value}", "IN_AADHAAR", gen_aadhaar, 10),
    ("My unique identification number is {value}.", "IN_AADHAAR", gen_aadhaar, 9),
    
    # PAN - High confidence
    ("My PAN card number is {value}.", "IN_PAN", gen_pan, 10),
    ("PAN: {value}", "IN_PAN", gen_pan, 10),
    ("Permanent Account Number: {value}", "IN_PAN", gen_pan, 10),
    ("For tax filing, PAN is {value}.", "IN_PAN", gen_pan, 9),
    ("Income tax PAN: {value}", "IN_PAN", gen_pan, 10),
    ("My tax ID is {value}.", "IN_PAN", gen_pan, 9),
    ("PAN number: {value}", "IN_PAN", gen_pan, 10),
    
    # Email - High confidence
    ("My email is {value}.", "EMAIL_ADDRESS", gen_email, 10),
    ("Contact me at {value}.", "EMAIL_ADDRESS", gen_email, 9),
    ("Email: {value}", "EMAIL_ADDRESS", gen_email, 10),
    ("Send documents to {value}.", "EMAIL_ADDRESS", gen_email, 8),
    ("You can reach me at {value}.", "EMAIL_ADDRESS", gen_email, 9),
    ("Email address: {value}", "EMAIL_ADDRESS", gen_email, 10),
    
    # Phone - High confidence
    ("My phone number is {value}.", "PHONE_NUMBER", gen_phone, 10),
    ("Call me at {value}.", "PHONE_NUMBER", gen_phone, 9),
    ("Mobile: {value}", "PHONE_NUMBER", gen_phone, 10),
    ("Contact number: {value}", "PHONE_NUMBER", gen_phone, 9),
    ("Phone: {value}", "PHONE_NUMBER", gen_phone, 10),
    ("Reach me on {value}.", "PHONE_NUMBER", gen_phone, 8),
    
    # Person - Medium confidence (names can be ambiguous)
    ("My name is {value}.", "PERSON", gen_name, 8),
    ("I am {value}.", "PERSON", gen_name, 7),
    ("This is {value} speaking.", "PERSON", gen_name, 8),
    ("Name: {value}", "PERSON", gen_name, 9),
    ("The applicant is {value}.", "PERSON", gen_name, 8),
    
    # SSN - High confidence
    ("My SSN is {value}.", "US_SSN", gen_ssn, 10),
    ("Social Security Number: {value}", "US_SSN", gen_ssn, 10),
    ("SSN: {value}", "US_SSN", gen_ssn, 10),
    
    # Credit Card - High confidence
    ("My credit card is {value}.", "CREDIT_CARD", gen_cc, 10),
    ("Card number: {value}", "CREDIT_CARD", gen_cc, 10),
    ("Credit card: {value}", "CREDIT_CARD", gen_cc, 10),
]

# ============================================================================
# Templates - NEGATIVE (NO PII - critical for reducing false positives)
# ============================================================================
NEGATIVE_TEMPLATES: List[str] = [
    # General text - no PII at all
    "The weather today is sunny with a high of 25 degrees.",
    "Please submit the report by Friday.",
    "The meeting is scheduled for 3 PM tomorrow.",
    "Thank you for your patience and understanding.",
    "The project deadline has been extended to next month.",
    "Please review the attached document carefully.",
    "The system will be under maintenance tonight.",
    "Your request has been processed successfully.",
    "The quarterly results exceeded expectations.",
    "Please confirm your attendance at the meeting.",
    "The documentation explains how neural networks process input data.",
    "It covers topics such as backpropagation and optimization techniques.",
    "Examples are provided using synthetic datasets.",
    "No real-world references are included in this document.",
    "The tutorial walks through the process of deploying an application.",
    "Best practices are highlighted throughout the guide.",
    "The research paper analyzes trends in renewable energy adoption.",
    "Graphs and charts are used to support the findings.",
    "The capital of France is Paris, known for its rich history.",
    "Popular landmarks include museums and monuments.",
    "Tourism contributes significantly to the local economy.",
    "The error code 503 indicates that the service is unavailable.",
    "Users are advised to retry after some time.",
    "Support teams monitor such incidents closely.",
    "Several technical challenges were discussed by the engineering team.",
    "No individual participants were identified in the meeting notes.",
    "The session concluded with agreed next steps.",
    "Bangalore has seen increased traffic congestion over the years.",
    "Several infrastructure projects are currently under development.",
    "Citizens have raised concerns about commute times.",
    "Authorities are evaluating long-term solutions.",
    "The new policy takes effect from next month.",
    "Please schedule a follow-up meeting with the team.",
    "The client approved the proposal yesterday.",
    "Database backup completed successfully.",
    "The API endpoint is now live.",
    "Please update your browser to the latest version.",
    "The application has been deployed to production.",
    "The server responded with a 200 status code.",
    "Engineers resolved the problem after restarting services.",
    "Monitoring has been improved to prevent recurrence.",
    "The user guide outlines steps to configure the application.",
    "Screenshots are included for clarity.",
    "No personal data is referenced anywhere in this document.",
    "The weather report indicates heavy rainfall in coastal regions.",
    "Several districts have issued alerts for residents.",
    "Emergency services are on standby.",
    "All data sources are publicly available.",
    
    # DANGEROUS NEGATIVES - Look like PII but aren't!
    "Order ID: 0123 4567 8901",  # Starts with 0, not Aadhaar
    "Transaction: 1234 5678 9012",  # Starts with 1, not Aadhaar
    "Reference: 0000 0000 0000",  # All zeros, not Aadhaar
    "Booking number: 1111 2222 3333",
    "Invoice #: 0987 6543 2109",
    "Ticket ID: 1000 2000 3000",
    "Confirmation: 0012 3456 7890",
    "Product code: ABCDE12345",  # Wrong PAN format
    "SKU: XYZDE9999X",  # Invalid 4th char for PAN
    "Model: ABCXY1234Z",  # Wrong format
    "Serial: QWERT12345",  # Not a PAN
    "Part number: LMNOP98765",
    "Account: 0123456789",  # Starts with 0, not phone
    "Policy: 1234567890",  # Starts with 1, not phone
    "Member ID: 5432109876",  # Starts with 5, not valid Indian mobile
    "Registration: 0000000000",
    "License: 1111111111",
    "Code: 000-00-0000",  # Invalid SSN (area 000)
    "Format: 666-12-3456",  # Invalid SSN (area 666)
    "Pattern: 900-00-0000",  # Invalid SSN (area 900+)
    "Version: 123-00-4567",  # Invalid group (00)
    "ID: 123-45-0000",  # Invalid serial (0000)
    "Use format: user@domain",  # Not real email
    "Pattern: name@company",  # Incomplete email
    "Example: test@example",  # Not real email
    "Template: {user}@{domain}.{tld}",  # Template, not email
    "Syntax: local@host",
    "Format should be x@y.z",
    "Version 1.2.3.4",  # Version number
    "Build: 10.0.19041",
    "Release: 2.0.0.1",
    "Server: 192.168.1.100",  # IP address
    "Gateway: 10.0.0.1",
    "Host: 172.16.0.50",
    "Location: 28.6139, 77.2090",  # Coordinates
    "GPS: 19.0760, 72.8777",
    "Promo code: SAVE20NOW",
    "Coupon: FLAT50OFF",
    "Voucher: ABC123XYZ",
    "PIN: 123456",  # Too short, not PII
    "OTP: 987654",  # OTP, not PII
    "Date: 12-34-5678",
    "DOB: 01/02/1990",  # Date format
    "Expiry: 2025-12-31",
    "Valid until: 31-12-2025",
    "Weight: 1234.5678 kg",
    "Amount: 9876543210",
    "Quantity: 1000000000",
    "Price: 12345.67",
]


def generate_dynamic_negative() -> str:
    """Generate dynamic negative samples for more variety."""
    templates = [
        # Business/Technical
        f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Omega', 'Phoenix', 'Atlas', 'Titan'])} is on track for Q{random.randint(1,4)} delivery.",
        f"The {random.choice(['backend', 'frontend', 'API', 'database', 'server', 'cache', 'queue'])} service responded in {random.randint(10, 500)}ms.",
        f"Build #{random.randint(1000, 9999)} completed {random.choice(['successfully', 'with warnings', 'without errors'])}.",
        f"Deployment to {random.choice(['staging', 'production', 'dev', 'QA', 'UAT'])} environment completed.",
        f"The {random.choice(['daily', 'weekly', 'monthly'])} report has been generated.",
        f"Meeting scheduled for {random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])} at {random.randint(9, 17)}:{random.choice(['00', '30'])}.",
        f"Task #{random.randint(100, 9999)} has been {random.choice(['assigned', 'completed', 'reviewed', 'approved'])}.",
        f"Sprint {random.randint(1, 50)} retrospective notes are available.",
        f"Version {random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 99)} has been released.",
        f"The {random.choice(['unit', 'integration', 'e2e', 'performance'])} tests passed with {random.randint(90, 100)}% coverage.",
        
        # General statements
        f"The weather in {random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad'])} is {random.choice(['sunny', 'cloudy', 'rainy', 'pleasant'])} today.",
        f"Traffic on {random.choice(['MG Road', 'Ring Road', 'Highway', 'Main Street'])} is {random.choice(['light', 'moderate', 'heavy'])}.",
        f"The {random.choice(['train', 'flight', 'bus'])} is expected to arrive at {random.randint(1, 12)}:{random.choice(['00', '15', '30', '45'])} {random.choice(['AM', 'PM'])}.",
        f"Stock price moved {random.choice(['up', 'down'])} by {random.uniform(0.5, 5.0):.2f}%.",
        f"The {random.choice(['quarterly', 'annual', 'monthly'])} revenue was {random.randint(10, 500)} {random.choice(['million', 'crore', 'lakh'])}.",
        f"Temperature is {random.randint(15, 40)}°C with {random.randint(30, 90)}% humidity.",
        f"The {random.choice(['movie', 'book', 'show', 'album'])} received a rating of {random.uniform(3.0, 5.0):.1f} stars.",
        f"Population of the {random.choice(['city', 'district', 'state'])} is approximately {random.randint(1, 50)} {random.choice(['million', 'lakh'])}.",
        
        # Technical IDs that look like PII but aren't
        f"Batch ID: {random.randint(1000000000, 9999999999)}",
        f"Session: {random.randint(10000, 99999)}-{random.randint(10000, 99999)}-{random.randint(10000, 99999)}",
        f"Trace ID: {random.randint(100000, 999999)}{random.randint(100000, 999999)}",
        f"Request #{random.randint(1000000, 9999999)}",
        f"Log entry: {random.randint(2020, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}Z",
        f"Hash: {hex(random.randint(0, 0xFFFFFFFF))[2:].upper()}",
        f"UUID segment: {random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
        f"Container ID: {random.choice(['abc', 'def', 'xyz', 'qrs'])}{random.randint(10000, 99999)}",
        f"Pod: {random.choice(['app', 'web', 'api', 'worker'])}-{str(random.randint(1000000, 9999999))[:7]}",
        f"Instance: i-{random.randint(10000000, 99999999)}",
    ]
    return random.choice(templates)


def create_positive_sample(template: str, entity_type: str, generator: callable, confidence: int) -> Dict:
    """Create a sample WITH PII - ensuring exact match."""
    value = generator()
    text = template.replace("{value}", value)
    start = text.find(value)
    end = start + len(value)
    
    # Verify the value exists at the position
    assert text[start:end] == value, f"Position mismatch: {text[start:end]} != {value}"
    
    output = {
        "flagged": True,
        "confidence": confidence,
        "entities": [{
            "type": entity_type,
            "value": value,
            "start": start,
            "end": end
        }],
        "reason": f"Detected {entity_type.replace('_', ' ').replace('IN ', '').title()}"
    }
    
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Analyze for PII: "{text}"'},
            {"role": "assistant", "content": json.dumps(output, indent=2)}
        ]
    }


def create_negative_sample(text: str) -> Dict:
    """Create a sample WITHOUT PII."""
    output = {
        "flagged": False,
        "confidence": 10,  # High confidence there's NO PII
        "entities": [],
        "reason": "No PII detected in text"
    }
    
    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Analyze for PII: "{text}"'},
            {"role": "assistant", "content": json.dumps(output, indent=2)}
        ]
    }


def add_variation_to_negative(text: str) -> str:
    """Add random variation to negative samples to increase diversity."""
    variations = [
        # Prepend variations
        ("", ""),
        ("Note: ", ""),
        ("FYI: ", ""),
        ("Update: ", ""),
        ("Info: ", ""),
        ("Status: ", ""),
        ("Message: ", ""),
        ("Alert: ", ""),
        ("Notice: ", ""),
        ("Reminder: ", ""),
    ]
    
    # Random prefix
    prefix, suffix = random.choice(variations)
    
    # Random number suffix for some samples
    if random.random() < 0.3:
        suffix = f" (Ref: {random.randint(1000, 9999)})"
    elif random.random() < 0.2:
        suffix = f" [{random.choice(['v1', 'v2', 'final', 'draft', 'updated'])}]"
    
    return prefix + text + suffix


def generate_unique_negative(used_texts: set) -> str:
    """Generate a unique negative sample, avoiding duplicates."""
    max_attempts = 100
    for _ in range(max_attempts):
        # 40% static templates, 30% dynamic, 30% static with variation
        choice = random.random()
        if choice < 0.4:
            # Use static template as-is
            text = random.choice(NEGATIVE_TEMPLATES)
        elif choice < 0.7:
            # Use dynamic generation
            text = generate_dynamic_negative()
        else:
            # Static with variation
            text = add_variation_to_negative(random.choice(NEGATIVE_TEMPLATES))
        
        if text not in used_texts:
            used_texts.add(text)
            return text
    
    # Fallback: always unique dynamic generation
    text = f"{generate_dynamic_negative()} (Ref: {random.randint(100000, 999999)})"
    used_texts.add(text)
    return text


def generate_dataset(num_samples: int = 10000, output_dir: str = "data") -> Tuple[str, str]:
    """Generate training and evaluation datasets."""
    os.makedirs(output_dir, exist_ok=True)
    
    num_positive = num_samples // 2
    num_negative = num_samples - num_positive
    
    print(f"Generating {num_positive} positive samples...")
    positive_samples = []
    used_positive_texts = set()
    for _ in range(num_positive):
        # Keep trying until we get a unique positive sample
        max_attempts = 50
        for _ in range(max_attempts):
            template, etype, gen, conf = random.choice(PII_TEMPLATES)
            sample = create_positive_sample(template, etype, gen, conf)
            user_text = sample['conversations'][1]['content']
            if user_text not in used_positive_texts:
                used_positive_texts.add(user_text)
                positive_samples.append(sample)
                break
        else:
            # Fallback: accept the sample even if duplicate
            positive_samples.append(sample)
    
    print(f"Generating {num_negative} negative samples...")
    negative_samples = []
    used_negative_texts = set()
    for _ in range(num_negative):
        text = generate_unique_negative(used_negative_texts)
        negative_samples.append(create_negative_sample(text))
    
    # Combine and shuffle
    all_samples = positive_samples + negative_samples
    random.shuffle(all_samples)
    
    # Split 80/20
    split_idx = int(len(all_samples) * 0.8)
    train_data = all_samples[:split_idx]
    eval_data = all_samples[split_idx:]
    
    # Save
    train_path = os.path.join(output_dir, "train_v2.jsonl")
    eval_path = os.path.join(output_dir, "eval_v2.jsonl")
    
    with open(train_path, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    with open(eval_path, 'w', encoding='utf-8') as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Stats
    print(f"\n[OK] Generated {len(train_data)} training samples -> {train_path}")
    print(f"[OK] Generated {len(eval_data)} evaluation samples -> {eval_path}")
    
    train_pos = sum(1 for s in train_data if json.loads(s['conversations'][2]['content'])['flagged'] == True)
    train_neg = len(train_data) - train_pos
    print(f"\nTraining distribution:")
    print(f"  Positive (flagged=true): {train_pos} ({100*train_pos/len(train_data):.1f}%)")
    print(f"  Negative (flagged=false): {train_neg} ({100*train_neg/len(train_data):.1f}%)")
    
    # Preview
    print("\n" + "="*70)
    print("SAMPLE PREVIEW")
    print("="*70)
    print("\n--- Positive Sample ---")
    print(json.dumps(positive_samples[0], indent=2))
    print("\n--- Negative Sample ---")
    print(json.dumps(negative_samples[0], indent=2))
    
    return train_path, eval_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PII training data v2")
    parser.add_argument("--samples", type=int, default=10000, help="Total samples")
    parser.add_argument("--output", type=str, default="data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    random.seed(args.seed)
    
    generate_dataset(args.samples, args.output)

