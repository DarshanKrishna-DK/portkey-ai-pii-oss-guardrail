"""
Pydantic Schemas for PII Guardrail API

Defines request/response models for Portkey webhook integration,
aligned with Presidio entity naming conventions.
"""

from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field


class DetectedEntity(BaseModel):
    """A single detected PII entity with location information."""
    
    type: str = Field(
        ..., 
        description="Presidio-compatible entity type (e.g., IN_AADHAAR, EMAIL_ADDRESS)",
        examples=["IN_AADHAAR", "IN_PAN", "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"]
    )
    value: str = Field(
        ..., 
        description="The actual PII text that was detected",
        examples=["2345 6789 0123", "ABCPD1234E", "user@example.com"]
    )
    start: int = Field(
        ..., 
        ge=0,
        description="Character start offset (0-indexed)",
        examples=[21, 0, 15]
    )
    end: int = Field(
        ..., 
        ge=0,
        description="Character end offset (exclusive)",
        examples=[35, 10, 31]
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for this specific entity detection"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "IN_AADHAAR",
                "value": "2345 6789 0123",
                "start": 21,
                "end": 35,
                "confidence": 0.95
            }
        }


class PIIResult(BaseModel):
    """Complete PII detection result with all metadata."""
    
    flagged: bool = Field(
        ..., 
        description="Whether any PII was detected in the text"
    )
    entities: List[DetectedEntity] = Field(
        default_factory=list,
        description="List of all detected PII entities with their positions"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Overall confidence score (highest among all entities, or 1.0 if no entities)"
    )
    severity: int = Field(
        ..., 
        ge=0, 
        le=10,
        description="Maximum severity score among detected entities (0 if none)"
    )
    reason: str = Field(
        ..., 
        description="Human-readable explanation of what was detected",
        examples=["Detected 1 Aadhaar number and 1 email address", "No PII detected"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "flagged": True,
                "entities": [
                    {"type": "IN_AADHAAR", "value": "2345 6789 0123", "start": 21, "end": 35}
                ],
                "confidence": 0.94,
                "severity": 10,
                "reason": "Detected 1 Aadhaar number"
            }
        }


class PortkeyWebhookRequest(BaseModel):
    """
    Request format from Portkey Gateway.
    
    Portkey sends the original request/response data to the webhook
    for guardrail evaluation.
    """
    
    request: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The original request sent to the LLM"
    )
    response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The response from the LLM (for output guardrails)"
    )
    
    # Additional context that Portkey may send
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata from Portkey"
    )


class PortkeyWebhookResponse(BaseModel):
    """
    Response format for Portkey webhook guardrails.
    
    Portkey expects:
    - verdict: "allow" or "block"
    - Optionally modified_request/modified_response for transformations
    """
    
    verdict: Literal["allow", "block"] = Field(
        ...,
        description="Guardrail verdict: 'allow' to proceed, 'block' to deny"
    )
    data: PIIResult = Field(
        ...,
        description="Detailed PII detection results"
    )
    modified_request: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Modified request if PII was redacted (optional)"
    )
    modified_response: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Modified response if PII was redacted (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "verdict": "block",
                "data": {
                    "flagged": True,
                    "entities": [
                        {"type": "IN_AADHAAR", "value": "2345 6789 0123", "start": 21, "end": 35}
                    ],
                    "confidence": 0.94,
                    "severity": 10,
                    "reason": "Detected 1 Aadhaar number"
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy", description="Service status")
    model_loaded: bool = Field(..., description="Whether the model is loaded")
    version: str = Field(..., description="API version")


class InferenceRequest(BaseModel):
    """Direct inference request (for testing without Portkey)."""
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text to analyze for PII"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "My Aadhaar number is 2345 6789 0123 and email is user@example.com"
            }
        }


class InferenceResponse(BaseModel):
    """Direct inference response."""
    
    result: PIIResult = Field(..., description="PII detection result")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    model_version: str = Field(..., description="Model version used")

    class Config:
        json_schema_extra = {
            "example": {
                "result": {
                    "flagged": True,
                    "entities": [
                        {"type": "IN_AADHAAR", "value": "2345 6789 0123", "start": 21, "end": 35}
                    ],
                    "confidence": 0.94,
                    "severity": 10,
                    "reason": "Detected 1 Aadhaar number"
                },
                "processing_time_ms": 45.2,
                "model_version": "1.0.0"
            }
        }


# Entity type constants (Presidio-aligned)
class EntityTypes:
    """Presidio-compatible entity type constants."""
    
    # Indian PII
    IN_AADHAAR = "IN_AADHAAR"
    IN_PAN = "IN_PAN"
    
    # General PII
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    
    # US PII
    US_SSN = "US_SSN"
    
    # Financial
    CREDIT_CARD = "CREDIT_CARD"
    
    # All supported types
    ALL = [
        IN_AADHAAR, IN_PAN, EMAIL_ADDRESS, PHONE_NUMBER,
        PERSON, LOCATION, US_SSN, CREDIT_CARD
    ]

