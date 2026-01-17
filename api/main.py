"""
FastAPI Webhook Server for PII Guardrail

Provides a Portkey-compatible webhook endpoint for PII detection
with fallback logic and observability support.
"""

import os
import time
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    PortkeyWebhookRequest,
    PortkeyWebhookResponse,
    PIIResult,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    DetectedEntity,
)
from .actions import (
    determine_action,
    should_trigger_fallback,
    map_action_to_verdict,
    get_portkey_status_code,
    Action,
)
from .model import PIIDetector, get_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pii-guardrail")

# API version
API_VERSION = "1.0.0"

# Global detector instance
detector: Optional[PIIDetector] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    global detector
    
    # Startup
    logger.info("Starting PII Guardrail API...")
    detector = PIIDetector(
        model_path=os.getenv("MODEL_PATH"),
        load_in_4bit=os.getenv("LOAD_IN_4BIT", "true").lower() == "true"
    )
    detector.load()
    logger.info("PII Guardrail API ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PII Guardrail API...")


# Create FastAPI app
app = FastAPI(
    title="PII Guardrail API",
    description="Portkey-compatible webhook for PII detection using fine-tuned Llama 3.2-1B",
    version=API_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=detector.is_loaded if detector else False,
        version=API_VERSION
    )


@app.post("/guardrail/pii", response_model=PortkeyWebhookResponse)
async def pii_guardrail(
    request: Request,
    response: Response,
    x_portkey_trace_id: Optional[str] = Header(None, alias="x-portkey-trace-id"),
):
    """
    Portkey webhook endpoint for PII detection.
    
    This endpoint is called by Portkey Gateway to evaluate requests/responses
    for PII before allowing them to proceed.
    
    Returns:
        PortkeyWebhookResponse with verdict and detection details
    """
    start_time = time.time()
    
    try:
        # Parse request body
        body = await request.json()
        webhook_request = PortkeyWebhookRequest(**body)
        
        # Extract text to analyze
        text = _extract_text_from_request(webhook_request)
        
        if not text:
            # No text to analyze
            return PortkeyWebhookResponse(
                verdict="allow",
                data=PIIResult(
                    flagged=False,
                    entities=[],
                    confidence=1.0,
                    severity=0,
                    reason="No text content to analyze"
                )
            )
        
        # Run PII detection
        entities, confidence = detector.detect(text)
        
        # Determine action
        action, result = determine_action(entities, confidence)
        
        # Map to Portkey verdict
        verdict = map_action_to_verdict(action)
        
        # Set appropriate status code
        status_code = get_portkey_status_code(action, result)
        response.status_code = status_code
        
        # Add fallback header if needed
        if should_trigger_fallback(result):
            response.headers["x-portkey-fallback"] = "true"
            logger.info(f"Fallback triggered for trace {x_portkey_trace_id}: confidence={result.confidence}")
        
        # Log the detection
        processing_time = (time.time() - start_time) * 1000
        _log_detection(
            trace_id=x_portkey_trace_id,
            action=action,
            result=result,
            processing_time_ms=processing_time
        )
        
        return PortkeyWebhookResponse(
            verdict=verdict,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        # On error, allow the request but flag it
        return PortkeyWebhookResponse(
            verdict="allow",
            data=PIIResult(
                flagged=False,
                entities=[],
                confidence=0.5,
                severity=0,
                reason=f"Error during analysis: {str(e)}"
            )
        )


@app.post("/detect", response_model=InferenceResponse)
async def detect_pii(request: InferenceRequest):
    """
    Direct PII detection endpoint (for testing without Portkey).
    
    Args:
        request: InferenceRequest with text to analyze
        
    Returns:
        InferenceResponse with detection results
    """
    start_time = time.time()
    
    # Run detection
    entities, confidence = detector.detect(request.text)
    
    # Determine action and result
    action, result = determine_action(entities, confidence)
    
    processing_time = (time.time() - start_time) * 1000
    
    return InferenceResponse(
        result=result,
        processing_time_ms=processing_time,
        model_version=API_VERSION
    )


@app.post("/analyze")
async def analyze_text(request: InferenceRequest):
    """
    Simple text analysis endpoint that returns raw detection results.
    
    Useful for debugging and testing the model.
    """
    start_time = time.time()
    
    entities, confidence = detector.detect(request.text)
    action, result = determine_action(entities, confidence)
    
    processing_time = (time.time() - start_time) * 1000
    
    return {
        "text": request.text,
        "flagged": result.flagged,
        "entities": [
            {
                "type": e.type,
                "value": e.value,
                "start": e.start,
                "end": e.end,
                "confidence": e.confidence
            }
            for e in result.entities
        ],
        "confidence": result.confidence,
        "severity": result.severity,
        "action": action.value,
        "reason": result.reason,
        "processing_time_ms": processing_time
    }


def _extract_text_from_request(webhook_request: PortkeyWebhookRequest) -> str:
    """
    Extract text content from the Portkey webhook request.
    
    Handles various request formats (chat completions, completions, etc.)
    """
    text_parts = []
    
    # Check request for input text
    if webhook_request.request:
        req = webhook_request.request
        
        # Chat completions format
        if "messages" in req:
            for msg in req.get("messages", []):
                if isinstance(msg, dict) and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        text_parts.append(content)
                    elif isinstance(content, list):
                        # Handle multi-part content
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
        
        # Completions format
        if "prompt" in req:
            prompt = req["prompt"]
            if isinstance(prompt, str):
                text_parts.append(prompt)
            elif isinstance(prompt, list):
                text_parts.extend(str(p) for p in prompt)
    
    # Check response for output text
    if webhook_request.response:
        resp = webhook_request.response
        
        # Chat completions response
        if "choices" in resp:
            for choice in resp.get("choices", []):
                if "message" in choice:
                    content = choice["message"].get("content", "")
                    if content:
                        text_parts.append(content)
                elif "text" in choice:
                    text_parts.append(choice["text"])
    
    return " ".join(text_parts)


def _log_detection(
    trace_id: Optional[str],
    action: Action,
    result: PIIResult,
    processing_time_ms: float
):
    """Log detection results for observability."""
    entity_types = [e.type for e in result.entities]
    
    log_data = {
        "trace_id": trace_id,
        "action": action.value,
        "flagged": result.flagged,
        "entity_count": len(result.entities),
        "entity_types": entity_types,
        "confidence": result.confidence,
        "severity": result.severity,
        "processing_time_ms": round(processing_time_ms, 2),
    }
    
    if action == Action.BLOCK:
        logger.warning(f"PII BLOCKED: {log_data}")
    elif result.flagged:
        logger.info(f"PII FLAGGED: {log_data}")
    else:
        logger.debug(f"PII CLEAN: {log_data}")


# Run with: uvicorn api.main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )

