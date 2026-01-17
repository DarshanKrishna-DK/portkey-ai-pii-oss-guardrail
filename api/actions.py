"""
Hybrid Action Logic for PII Guardrail

Implements BLOCK/FLAG/ALLOW logic based on severity thresholds
and confidence scores, aligned with Guardrails AI on_fail strategies.
"""

from typing import List, Tuple
from enum import Enum

from .schemas import DetectedEntity, PIIResult


class Action(str, Enum):
    """Possible guardrail actions."""
    BLOCK = "BLOCK"   # Deny the request (high severity PII)
    FLAG = "FLAG"     # Log and allow (low severity PII)
    ALLOW = "ALLOW"   # Allow without concern


# Severity scores for each entity type (1-10 scale)
# Higher = more sensitive
SEVERITY_SCORES = {
    "IN_AADHAAR": 10,      # Critical - National ID
    "IN_PAN": 9,           # Critical - Tax ID  
    "US_SSN": 10,          # Critical - Social Security
    "CREDIT_CARD": 9,      # Critical - Financial
    "US_BANK_NUMBER": 8,   # High - Financial
    "US_PASSPORT": 8,      # High - Government ID
    "US_DRIVER_LICENSE": 7, # High - Government ID
    "IBAN_CODE": 7,        # High - Financial
    "IP_ADDRESS": 4,       # Medium - Network identifier
    "EMAIL_ADDRESS": 3,    # Low - Contact info
    "PHONE_NUMBER": 3,     # Low - Contact info
    "PERSON": 2,           # Low - Name only
    "LOCATION": 2,         # Low - General location
    "DATE_TIME": 1,        # Minimal - Temporal info
    "URL": 2,              # Low - Web address
    "DOMAIN_NAME": 2,      # Low - Domain
}

# Thresholds for action determination
BLOCK_THRESHOLD = 8      # Severity > 8 -> BLOCK
FLAG_THRESHOLD = 4       # Severity < 4 -> FLAG only
CONFIDENCE_THRESHOLD = 0.6  # Below this -> trigger fallback


def get_severity(entity_type: str) -> int:
    """Get severity score for an entity type."""
    return SEVERITY_SCORES.get(entity_type, 5)  # Default to medium


def calculate_max_severity(entities: List[DetectedEntity]) -> int:
    """Calculate the maximum severity among detected entities."""
    if not entities:
        return 0
    return max(get_severity(e.type) for e in entities)


def generate_reason(entities: List[DetectedEntity], action: Action) -> str:
    """Generate a human-readable reason for the detection result."""
    if not entities:
        return "No PII detected"
    
    # Count entities by type
    entity_counts = {}
    for e in entities:
        entity_counts[e.type] = entity_counts.get(e.type, 0) + 1
    
    # Build reason parts
    reason_parts = []
    for etype, count in sorted(entity_counts.items()):
        # Make the type more readable
        readable = etype.replace("_", " ").replace("IN ", "").replace("US ", "").title()
        reason_parts.append(f"{count} {readable}")
    
    detected_str = ", ".join(reason_parts)
    
    if action == Action.BLOCK:
        return f"BLOCKED: Critical PII detected - {detected_str}"
    elif action == Action.FLAG:
        return f"FLAGGED: {detected_str} - logged for review"
    else:
        return f"Detected {detected_str}"


def determine_action(
    entities: List[DetectedEntity], 
    model_confidence: float
) -> Tuple[Action, PIIResult]:
    """
    Determine the appropriate action based on detected entities and confidence.
    
    Hybrid Action Logic (aligned with Guardrails AI on_fail strategies):
    - Severity > 8 (e.g., SSN, Aadhaar): ACTION = BLOCK
    - Severity < 4 (e.g., Name, Location): ACTION = FLAG & LOG
    - Confidence < 0.6: Trigger fallback to GPT-4o
    
    Args:
        entities: List of detected PII entities
        model_confidence: Model's confidence score (0.0-1.0)
        
    Returns:
        Tuple of (Action, PIIResult)
    """
    # No entities detected
    if not entities:
        return Action.ALLOW, PIIResult(
            flagged=False,
            entities=[],
            confidence=model_confidence,
            severity=0,
            reason="No PII detected"
        )
    
    # Calculate metrics
    max_severity = calculate_max_severity(entities)
    max_entity_confidence = max(
        (e.confidence for e in entities if e.confidence is not None), 
        default=model_confidence
    )
    overall_confidence = min(model_confidence, max_entity_confidence)
    
    # Determine action based on severity thresholds
    if max_severity > BLOCK_THRESHOLD:
        # High severity PII (Aadhaar, SSN, etc.) -> BLOCK
        action = Action.BLOCK
        critical_types = [e.type for e in entities if get_severity(e.type) > BLOCK_THRESHOLD]
        
    elif max_severity < FLAG_THRESHOLD:
        # Low severity PII (names, locations) -> FLAG only
        action = Action.FLAG
        
    else:
        # Medium severity -> depends on confidence
        if overall_confidence >= CONFIDENCE_THRESHOLD:
            action = Action.FLAG
        else:
            # Low confidence on medium severity -> FLAG with fallback
            action = Action.FLAG
    
    # Generate reason
    reason = generate_reason(entities, action)
    
    # Check if fallback should be triggered
    fallback_triggered = overall_confidence < CONFIDENCE_THRESHOLD
    if fallback_triggered:
        reason += " (low confidence - fallback recommended)"
    
    return action, PIIResult(
        flagged=True,
        entities=entities,
        confidence=overall_confidence,
        severity=max_severity,
        reason=reason
    )


def should_trigger_fallback(result: PIIResult) -> bool:
    """
    Determine if the GPT-4o fallback should be triggered.
    
    Fallback is triggered when:
    - Confidence is below threshold (0.6)
    - Or when there's uncertainty in detection
    """
    return result.confidence < CONFIDENCE_THRESHOLD


def map_action_to_verdict(action: Action) -> str:
    """Map internal action to Portkey verdict."""
    if action == Action.BLOCK:
        return "block"
    else:
        # Both FLAG and ALLOW map to "allow" in Portkey
        # The difference is in logging/observability
        return "allow"


def get_portkey_status_code(action: Action, result: PIIResult) -> int:
    """
    Get the appropriate HTTP status code for Portkey.
    
    Portkey status codes:
    - 200: Guardrails passed
    - 246: Guardrails failed but DENY=FALSE (process anyway)
    - 446: Guardrails failed and DENY=TRUE (block request)
    """
    if action == Action.BLOCK:
        return 446  # Block the request
    elif action == Action.FLAG and result.flagged:
        return 246  # Flag but allow
    else:
        return 200  # Clean pass

