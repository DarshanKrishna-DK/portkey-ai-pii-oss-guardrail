"""
Context-Rich Sentence Templates for PII Synthetic Data Generation

Templates include context words that help the model learn contextual patterns
for improved detection accuracy, aligned with Presidio's context enhancement approach.
"""

from typing import List, Dict

# Templates with single entity types
AADHAAR_TEMPLATES: List[str] = [
    # With strong context
    "My Aadhaar number is {IN_AADHAAR}.",
    "Please verify my UIDAI Aadhaar: {IN_AADHAAR}.",
    "Aadhaar Card Number: {IN_AADHAAR}",
    "My unique identification number is {IN_AADHAAR}.",
    "UID: {IN_AADHAAR} for KYC verification.",
    "Aadhaar: {IN_AADHAAR}",
    "My aadhaar no is {IN_AADHAAR}, please update the records.",
    "For Aadhaar verification, use {IN_AADHAAR}.",
    "The customer's Aadhaar is {IN_AADHAAR}.",
    "Aadhaar ID {IN_AADHAAR} has been registered.",
    
    # With weaker context (harder cases)
    "ID number {IN_AADHAAR} is on file.",
    "Please use {IN_AADHAAR} for identity verification.",
    "The 12-digit number {IN_AADHAAR} belongs to the applicant.",
    "Reference: {IN_AADHAAR}",
    "Document shows {IN_AADHAAR} as the identifier.",
]

PAN_TEMPLATES: List[str] = [
    # With strong context
    "My PAN card number is {IN_PAN}.",
    "PAN: {IN_PAN}",
    "Permanent Account Number: {IN_PAN}",
    "For tax purposes, my PAN is {IN_PAN}.",
    "Income tax PAN: {IN_PAN}",
    "My tax ID is {IN_PAN}.",
    "PAN Number: {IN_PAN} for ITR filing.",
    "The taxpayer's PAN is {IN_PAN}.",
    "PAN card: {IN_PAN}",
    "Tax identification: {IN_PAN}",
    
    # With weaker context
    "ID: {IN_PAN}",
    "Please verify {IN_PAN} in your records.",
    "The alphanumeric code {IN_PAN} is registered.",
    "Reference number: {IN_PAN}",
]

EMAIL_TEMPLATES: List[str] = [
    # With strong context
    "My email address is {EMAIL_ADDRESS}.",
    "Contact me at {EMAIL_ADDRESS}.",
    "Email: {EMAIL_ADDRESS}",
    "Send the documents to {EMAIL_ADDRESS}.",
    "You can reach me at {EMAIL_ADDRESS}.",
    "Mail ID: {EMAIL_ADDRESS}",
    "Please email {EMAIL_ADDRESS} for more information.",
    "My e-mail is {EMAIL_ADDRESS}.",
    "Write to {EMAIL_ADDRESS} for support.",
    "Email address: {EMAIL_ADDRESS}",
    
    # With weaker context
    "Reply to {EMAIL_ADDRESS}.",
    "{EMAIL_ADDRESS} is the contact.",
    "Forward this to {EMAIL_ADDRESS}.",
]

PHONE_TEMPLATES: List[str] = [
    # With strong context
    "My phone number is {PHONE_NUMBER}.",
    "Call me at {PHONE_NUMBER}.",
    "Mobile: {PHONE_NUMBER}",
    "Contact number: {PHONE_NUMBER}",
    "Reach me on {PHONE_NUMBER}.",
    "Phone: {PHONE_NUMBER}",
    "My mobile number is {PHONE_NUMBER}.",
    "Telephone: {PHONE_NUMBER}",
    "Cell: {PHONE_NUMBER}",
    "Call {PHONE_NUMBER} for assistance.",
    
    # With weaker context
    "Dial {PHONE_NUMBER}.",
    "Number: {PHONE_NUMBER}",
    "{PHONE_NUMBER} is the contact.",
]

PERSON_TEMPLATES: List[str] = [
    # With strong context
    "My name is {PERSON}.",
    "I am {PERSON}.",
    "This is {PERSON} speaking.",
    "Mr. {PERSON} has arrived.",
    "Ms. {PERSON} will handle this.",
    "Dr. {PERSON} is the specialist.",
    "The applicant is {PERSON}.",
    "Name: {PERSON}",
    "Called {PERSON} regarding the matter.",
    "Person: {PERSON}",
    
    # With weaker context
    "{PERSON} submitted the application.",
    "Regards, {PERSON}",
    "From: {PERSON}",
]

SSN_TEMPLATES: List[str] = [
    # With strong context
    "My SSN is {US_SSN}.",
    "Social Security Number: {US_SSN}",
    "SSN: {US_SSN}",
    "My social security is {US_SSN}.",
    "SS Number: {US_SSN}",
    "Social security number: {US_SSN}",
    
    # With weaker context
    "The number {US_SSN} is on file.",
    "ID: {US_SSN}",
]

CREDIT_CARD_TEMPLATES: List[str] = [
    # With strong context
    "My credit card number is {CREDIT_CARD}.",
    "Card Number: {CREDIT_CARD}",
    "Visa: {CREDIT_CARD}",
    "Mastercard: {CREDIT_CARD}",
    "Pay with card {CREDIT_CARD}.",
    "Credit card: {CREDIT_CARD}",
    "Debit card number: {CREDIT_CARD}",
    "CC: {CREDIT_CARD}",
    "Payment card: {CREDIT_CARD}",
    
    # With weaker context
    "Use {CREDIT_CARD} for payment.",
    "Card: {CREDIT_CARD}",
]

# Multi-entity templates (more complex scenarios)
MULTI_ENTITY_TEMPLATES: List[str] = [
    # Two entities
    "Contact {PERSON} at {EMAIL_ADDRESS}.",
    "My name is {PERSON} and my email is {EMAIL_ADDRESS}.",
    "{PERSON}'s phone number is {PHONE_NUMBER}.",
    "Name: {PERSON}, Email: {EMAIL_ADDRESS}",
    "User {PERSON} with Aadhaar {IN_AADHAAR} registered.",
    "{PERSON}'s PAN is {IN_PAN}.",
    "Contact {PERSON} on {PHONE_NUMBER} or {EMAIL_ADDRESS}.",
    
    # Three entities
    "Name: {PERSON}, Email: {EMAIL_ADDRESS}, Phone: {PHONE_NUMBER}",
    "{PERSON} (Aadhaar: {IN_AADHAAR}, PAN: {IN_PAN}) completed KYC.",
    "Customer {PERSON} with email {EMAIL_ADDRESS} and phone {PHONE_NUMBER}.",
    "Applicant: {PERSON}, Aadhaar: {IN_AADHAAR}, Email: {EMAIL_ADDRESS}",
    
    # Four or more entities (complex)
    "User {PERSON} registered with Aadhaar {IN_AADHAAR}, PAN {IN_PAN}, and email {EMAIL_ADDRESS}.",
    "KYC Details - Name: {PERSON}, Aadhaar: {IN_AADHAAR}, PAN: {IN_PAN}, Phone: {PHONE_NUMBER}",
    "Profile: {PERSON}, Email: {EMAIL_ADDRESS}, Mobile: {PHONE_NUMBER}, Aadhaar: {IN_AADHAAR}",
]

# Negative templates (no PII - important for balanced training)
NEGATIVE_TEMPLATES: List[str] = [
    # General statements
    "The weather today is sunny with a high of 25 degrees.",
    "Please submit the report by Friday.",
    "The meeting is scheduled for 3 PM tomorrow.",
    "Thank you for your patience.",
    "The project deadline has been extended.",
    "Please review the attached document.",
    "The system will be under maintenance tonight.",
    "Your request has been processed successfully.",
    "The new policy takes effect from next month.",
    "Please confirm your attendance.",
    
    # Business context (no PII)
    "The quarterly results exceeded expectations.",
    "Our team completed the project ahead of schedule.",
    "The client approved the proposal.",
    "Please schedule a follow-up meeting.",
    "The invoice has been sent for processing.",
    
    # Technical context (no PII)
    "The server responded with a 200 status code.",
    "Database backup completed successfully.",
    "The API endpoint is now live.",
    "Please update your browser to the latest version.",
    "The application has been deployed to production.",
    
    # Ambiguous (looks like PII but isn't)
    "The product code is ABC12345XY.",
    "Order number: 123456789012",
    "Reference ID: ABCD1234EFGH",
    "Transaction ID: 9876543210",
    "The serial number is 1234-5678-9012.",
]

# Edge case templates (tricky scenarios)
EDGE_CASE_TEMPLATES: List[str] = [
    # PII in unusual positions
    "{IN_AADHAAR} is my Aadhaar number.",
    "{EMAIL_ADDRESS} - that's my email.",
    "Here it is: {IN_PAN}",
    
    # Multiple same-type entities
    "Primary email: {EMAIL_ADDRESS}, Secondary email: {EMAIL_ADDRESS}",
    "Home: {PHONE_NUMBER}, Work: {PHONE_NUMBER}",
    
    # PII with surrounding noise
    "Note: {PERSON}'s details are confidential.",
    "[IMPORTANT] Aadhaar: {IN_AADHAAR}",
    "***{EMAIL_ADDRESS}*** is the contact.",
    
    # Informal/conversational
    "hey my aadhaar is {IN_AADHAAR} pls check",
    "email me at {EMAIL_ADDRESS} asap",
    "call {PHONE_NUMBER} urgent",
    
    # Mixed case and formatting
    "AADHAAR: {IN_AADHAAR}",
    "EMAIL: {EMAIL_ADDRESS}",
    "PAN CARD: {IN_PAN}",
]

# Combine all templates
TEMPLATES: Dict[str, List[str]] = {
    "IN_AADHAAR": AADHAAR_TEMPLATES,
    "IN_PAN": PAN_TEMPLATES,
    "EMAIL_ADDRESS": EMAIL_TEMPLATES,
    "PHONE_NUMBER": PHONE_TEMPLATES,
    "PERSON": PERSON_TEMPLATES,
    "US_SSN": SSN_TEMPLATES,
    "CREDIT_CARD": CREDIT_CARD_TEMPLATES,
    "MULTI_ENTITY": MULTI_ENTITY_TEMPLATES,
    "NEGATIVE": NEGATIVE_TEMPLATES,
    "EDGE_CASES": EDGE_CASE_TEMPLATES,
}

# All single-entity templates combined
ALL_SINGLE_ENTITY_TEMPLATES: List[str] = (
    AADHAAR_TEMPLATES + PAN_TEMPLATES + EMAIL_TEMPLATES + 
    PHONE_TEMPLATES + PERSON_TEMPLATES + SSN_TEMPLATES + CREDIT_CARD_TEMPLATES
)

# All templates combined
ALL_TEMPLATES: List[str] = (
    ALL_SINGLE_ENTITY_TEMPLATES + MULTI_ENTITY_TEMPLATES + 
    NEGATIVE_TEMPLATES + EDGE_CASE_TEMPLATES
)


def get_templates_for_entity(entity_type: str) -> List[str]:
    """Get all templates containing a specific entity type."""
    return TEMPLATES.get(entity_type, [])


def get_template_distribution() -> Dict[str, int]:
    """Get the count of templates per category."""
    return {key: len(templates) for key, templates in TEMPLATES.items()}

