"""
Model Loading and Inference for PII Guardrail

Handles loading the fine-tuned LoRA adapters and running inference
for PII detection.
"""

import os
import re
import json
import time
from typing import List, Tuple, Optional
from pathlib import Path

from .schemas import DetectedEntity


# System prompt for the model (must match training prompt)
SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection and risk assessment system.

TASK: Analyze text, identify PII entities, and assess their risk level.

=== STRICT EXTRACTION RULES ===
1. ONLY report PII that EXACTLY exists in the input text
2. The "value" field must be a VERBATIM substring from the input
3. "start" and "end" must be correct character positions
4. If NO PII exists, return flagged: false with empty entities
5. NEVER invent, guess, or hallucinate PII values

=== RISK-BASED CLASSIFICATION ===

HIGH RISK (flag immediately, confidence 9-10):
- Email addresses (any format)
- Phone numbers (with country code or local)
- Government IDs: Aadhaar, PAN, SSN, Passport
- Credit/Debit card numbers
- Full residential addresses
- Bank account numbers
- Full name + contact detail combination

MEDIUM RISK (flag with caution, confidence 6-8):
- Full name + city/location
- Full name + workplace/company
- Employee/Customer ID numbers
- Date of birth with other identifiers
- IP addresses in user context

LOW RISK (usually don't flag, confidence 1-5):
- First name only (no surname)
- Role-based mentions (CEO, Manager, Candidate)
- General city/country without identity link
- Public figures in news context
- Fictional characters
- Generic reference numbers (Order ID, Ticket #)

=== PII TYPES TO DETECT ===
- PERSON: Full names (first + last name together)
- EMAIL: Email addresses (user@domain.com)
- PHONE: Phone numbers (+91 XXXXX XXXXX, XXX-XXX-XXXX)
- IN_AADHAAR: Indian Aadhaar (12 digits: XXXX XXXX XXXX)
- IN_PAN: Indian PAN (ABCDE1234F format)
- US_SSN: US Social Security (XXX-XX-XXXX)
- CREDIT_CARD: Card numbers (13-19 digits)

=== OUTPUT FORMAT (JSON only) ===
{
  "flagged": true/false,
  "confidence": 1-10,
  "entities": [{"type": "TYPE", "value": "exact_text", "start": N, "end": N}],
  "reason": "brief explanation with risk assessment"
}

=== CONFIDENCE SCORING ===
- 9-10: HIGH RISK - Clear PII with explicit context ("My Aadhaar is", "Email:")
- 6-8: MEDIUM RISK - PII present but context is ambiguous
- 3-5: LOW RISK - Pattern matches but likely not sensitive
- 1-2: Very uncertain - Could be false positive

CRITICAL: If the value does not exist verbatim in the input, do NOT report it."""


class PIIDetector:
    """
    PII Detection model wrapper.
    
    Loads the fine-tuned Llama 3.2-1B model with LoRA adapters
    and provides inference methods.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        load_in_4bit: bool = True,
    ):
        """
        Initialize the PII detector.
        
        Args:
            model_path: Path to LoRA adapters (or None to use env var)
            device: Device to load model on ("auto", "cuda", "cpu")
            load_in_4bit: Whether to use 4-bit quantization
        """
        self.model_path = model_path or os.getenv("MODEL_PATH", "pii-guardrail-model/lora_adapters")
        self.device = device
        self.load_in_4bit = load_in_4bit
        
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
    def load(self) -> bool:
        """
        Load the model and tokenizer.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            from unsloth import FastLanguageModel
            
            print(f"Loading model from: {self.model_path}")
            
            # Check if path exists
            if not Path(self.model_path).exists():
                print(f"Warning: Model path {self.model_path} does not exist")
                print("Using base model for demonstration...")
                model_name = "unsloth/Llama-3.2-1B-Instruct"
            else:
                model_name = self.model_path
            
            # Load model
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_name,
                max_seq_length=512,
                load_in_4bit=self.load_in_4bit,
                dtype=None,
            )
            
            # Set to inference mode
            FastLanguageModel.for_inference(self.model)
            
            self.is_loaded = True
            print("Model loaded successfully!")
            return True
            
        except ImportError:
            print("Warning: unsloth not installed. Using mock inference.")
            self.is_loaded = False
            return False
            
        except Exception as e:
            print(f"Error loading model: {e}")
            self.is_loaded = False
            return False
    
    def _parse_model_output(self, output_text: str, input_text: str = "") -> Tuple[List[DetectedEntity], float, bool, str]:
        """
        Parse the model's JSON output.
        
        Returns:
            Tuple of (entities, confidence, flagged, reason)
        """
        try:
            # Find JSON in output
            start = output_text.find('{')
            end = output_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = output_text[start:end]
                data = json.loads(json_str)
                
                entities = []
                for e in data.get('entities', []):
                    value = e.get('value', '')
                    
                    # Grounding validation: only include entities that exist in input
                    if input_text and value and value not in input_text:
                        print(f"Grounding check: '{value}' not found in input, skipping")
                        continue
                    
                    # Recalculate start/end positions for grounding
                    if input_text and value:
                        actual_start = input_text.find(value)
                        if actual_start >= 0:
                            e['start'] = actual_start
                            e['end'] = actual_start + len(value)
                    
                    entities.append(DetectedEntity(
                        type=e.get('type', 'UNKNOWN'),
                        value=value,
                        start=e.get('start', 0),
                        end=e.get('end', 0),
                        confidence=e.get('confidence')
                    ))
                
                # Model outputs confidence 1-10, convert to 0-1 for API
                raw_confidence = data.get('confidence', 5)
                normalized_confidence = raw_confidence / 10.0 if raw_confidence > 1 else raw_confidence
                
                # If grounding removed all entities, unflag
                flagged = data.get('flagged', False) and len(entities) > 0
                reason = data.get('reason', '')
                if data.get('flagged', False) and len(entities) == 0:
                    reason = "No valid PII after grounding validation"
                
                return (
                    entities,
                    normalized_confidence,
                    flagged,
                    reason
                )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing model output: {e}")
        
        return [], 0.5, False, "Failed to parse model output"
    
    def detect(self, text: str) -> Tuple[List[DetectedEntity], float]:
        """
        Detect PII entities in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (list of detected entities, confidence score)
        """
        if not self.is_loaded:
            # Fall back to regex-based detection
            return self._regex_fallback(text)
        
        try:
            import torch
            
            # Prepare input (must match training format)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f'Analyze for PII: "{text}"'}
            ]
            
            inputs = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt"
            ).to(self.model.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=256,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode output
            output_text = self.tokenizer.decode(
                outputs[0][inputs.shape[1]:], 
                skip_special_tokens=True
            )
            
            # Parse output with grounding validation
            entities, confidence, _, _ = self._parse_model_output(output_text, text)
            return entities, confidence
            
        except Exception as e:
            print(f"Inference error: {e}")
            return self._regex_fallback(text)
    
    def _regex_fallback(self, text: str) -> Tuple[List[DetectedEntity], float]:
        """
        Fallback to regex-based detection when model is unavailable.
        
        This provides basic functionality for testing without the model.
        """
        entities = []
        
        # Aadhaar pattern (12 digits with optional spaces)
        aadhaar_pattern = r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b'
        for match in re.finditer(aadhaar_pattern, text):
            entities.append(DetectedEntity(
                type="IN_AADHAAR",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.85
            ))
        
        # PAN pattern
        pan_pattern = r'\b[A-Z]{5}\d{4}[A-Z]\b'
        for match in re.finditer(pan_pattern, text):
            entities.append(DetectedEntity(
                type="IN_PAN",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        
        # Email pattern
        email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            entities.append(DetectedEntity(
                type="EMAIL_ADDRESS",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95
            ))
        
        # Phone pattern (Indian)
        phone_pattern = r'(?:\+?91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}'
        for match in re.finditer(phone_pattern, text):
            entities.append(DetectedEntity(
                type="PHONE_NUMBER",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.8
            ))
        
        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        for match in re.finditer(ssn_pattern, text):
            entities.append(DetectedEntity(
                type="US_SSN",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.9
            ))
        
        # Calculate overall confidence
        if entities:
            confidence = sum(e.confidence or 0.8 for e in entities) / len(entities)
        else:
            confidence = 1.0  # High confidence that there's no PII
        
        return entities, confidence


# Global detector instance (lazy loaded)
_detector: Optional[PIIDetector] = None


def get_detector() -> PIIDetector:
    """Get or create the global detector instance."""
    global _detector
    if _detector is None:
        _detector = PIIDetector()
        _detector.load()
    return _detector


def detect_pii(text: str) -> Tuple[List[DetectedEntity], float]:
    """
    Convenience function to detect PII in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (entities, confidence)
    """
    detector = get_detector()
    return detector.detect(text)

