"""
Gemini-Based Synthetic PII Data Generator

Uses Gemini 1.5 Pro as a teacher model with a verification loop
to generate high-quality synthetic PII training data.
"""

import os
import re
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

from .config import ENTITY_CONFIG, SEVERITY_SCORES, get_generator
from .templates import (
    TEMPLATES, ALL_SINGLE_ENTITY_TEMPLATES, 
    MULTI_ENTITY_TEMPLATES, NEGATIVE_TEMPLATES, EDGE_CASE_TEMPLATES
)
from .validators import validate_entity


@dataclass
class DetectedEntity:
    """Represents a detected PII entity with location information."""
    type: str
    value: str
    start: int
    end: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrainingSample:
    """A single training sample with text and annotations."""
    text: str
    entities: List[DetectedEntity] = field(default_factory=list)
    flagged: bool = False
    confidence: float = 1.0
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entities": [e.to_dict() for e in self.entities],
            "flagged": self.flagged,
            "confidence": self.confidence,
            "reason": self.reason,
        }
    
    def to_training_format(self) -> Dict[str, Any]:
        """Convert to the instruction-tuned training format."""
        return {
            "instruction": f'Detect PII in: "{self.text}"',
            "output": json.dumps({
                "flagged": self.flagged,
                "entities": [e.to_dict() for e in self.entities],
                "confidence": self.confidence,
                "reason": self.reason,
            }, indent=2)
        }


class PIIDataGenerator:
    """
    Generates synthetic PII training data using templates and
    optionally Gemini for enhanced diversity.
    """
    
    def __init__(
        self, 
        gemini_api_key: Optional[str] = None,
        use_gemini: bool = False,
        seed: Optional[int] = None
    ):
        """
        Initialize the generator.
        
        Args:
            gemini_api_key: API key for Gemini (optional)
            use_gemini: Whether to use Gemini for enhanced generation
            seed: Random seed for reproducibility
        """
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.use_gemini = use_gemini and self.gemini_api_key is not None
        
        if seed is not None:
            random.seed(seed)
        
        self.gemini_client = None
        if self.use_gemini:
            self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini client."""
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        except ImportError:
            print("Warning: google-genai not installed. Using template-only generation.")
            self.use_gemini = False
    
    def _find_entity_positions(self, text: str, value: str) -> List[Tuple[int, int]]:
        """Find all occurrences of a value in text."""
        positions = []
        start = 0
        while True:
            idx = text.find(value, start)
            if idx == -1:
                break
            positions.append((idx, idx + len(value)))
            start = idx + 1
        return positions
    
    def _generate_from_template(self, template: str) -> TrainingSample:
        """Generate a sample from a template by filling in placeholders."""
        text = template
        entities = []
        
        # Find all placeholders in the template
        placeholders = re.findall(r'\{([A-Z_]+)\}', template)
        
        # Track replacements to handle multiple same-type entities
        replacements = {}
        
        for placeholder in placeholders:
            if placeholder in ENTITY_CONFIG:
                # Generate a value for this entity type
                generator = get_generator(placeholder)
                value = generator()
                
                # Store for replacement
                if placeholder not in replacements:
                    replacements[placeholder] = []
                replacements[placeholder].append(value)
        
        # Replace placeholders and track positions
        for entity_type, values in replacements.items():
            for value in values:
                # Replace one occurrence at a time
                placeholder = f"{{{entity_type}}}"
                if placeholder in text:
                    start = text.find(placeholder)
                    text = text.replace(placeholder, value, 1)
                    end = start + len(value)
                    
                    entities.append(DetectedEntity(
                        type=entity_type,
                        value=value,
                        start=start,
                        end=end
                    ))
        
        # Recalculate positions after all replacements (they may have shifted)
        final_entities = []
        for entity in entities:
            positions = self._find_entity_positions(text, entity.value)
            if positions:
                # Use the first position found
                start, end = positions[0]
                final_entities.append(DetectedEntity(
                    type=entity.type,
                    value=entity.value,
                    start=start,
                    end=end
                ))
        
        # Sort entities by start position
        final_entities.sort(key=lambda e: e.start)
        
        # Generate reason
        if final_entities:
            entity_counts = {}
            for e in final_entities:
                entity_counts[e.type] = entity_counts.get(e.type, 0) + 1
            
            reason_parts = []
            for etype, count in entity_counts.items():
                readable_name = etype.replace("_", " ").replace("IN ", "").title()
                reason_parts.append(f"{count} {readable_name}")
            
            reason = "Detected " + ", ".join(reason_parts)
        else:
            reason = "No PII detected"
        
        return TrainingSample(
            text=text,
            entities=final_entities,
            flagged=len(final_entities) > 0,
            confidence=1.0,
            reason=reason
        )
    
    def generate_single_entity_samples(self, count: int) -> List[TrainingSample]:
        """Generate samples with single entity types."""
        samples = []
        
        for entity_type, templates in TEMPLATES.items():
            if entity_type in ["MULTI_ENTITY", "NEGATIVE", "EDGE_CASES"]:
                continue
            
            # Calculate samples per entity type
            samples_per_type = count // len([k for k in TEMPLATES.keys() 
                                             if k not in ["MULTI_ENTITY", "NEGATIVE", "EDGE_CASES"]])
            
            for _ in range(samples_per_type):
                template = random.choice(templates)
                sample = self._generate_from_template(template)
                samples.append(sample)
        
        return samples
    
    def generate_multi_entity_samples(self, count: int) -> List[TrainingSample]:
        """Generate samples with multiple entities."""
        samples = []
        
        for _ in range(count):
            template = random.choice(MULTI_ENTITY_TEMPLATES)
            sample = self._generate_from_template(template)
            samples.append(sample)
        
        return samples
    
    def generate_negative_samples(self, count: int) -> List[TrainingSample]:
        """Generate samples without any PII."""
        samples = []
        
        for _ in range(count):
            template = random.choice(NEGATIVE_TEMPLATES)
            sample = TrainingSample(
                text=template,
                entities=[],
                flagged=False,
                confidence=1.0,
                reason="No PII detected"
            )
            samples.append(sample)
        
        return samples
    
    def generate_edge_case_samples(self, count: int) -> List[TrainingSample]:
        """Generate edge case samples."""
        samples = []
        
        for _ in range(count):
            template = random.choice(EDGE_CASE_TEMPLATES)
            sample = self._generate_from_template(template)
            samples.append(sample)
        
        return samples
    
    def _generate_with_gemini(self, prompt: str) -> Optional[str]:
        """Use Gemini to generate enhanced samples."""
        if not self.gemini_client:
            return None
        
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt,
                config={
                    "temperature": 0.8,
                    "max_output_tokens": 1024,
                }
            )
            return response.text
        except Exception as e:
            print(f"Gemini generation error: {e}")
            return None
    
    def generate_gemini_enhanced_samples(self, count: int) -> List[TrainingSample]:
        """
        Use Gemini to generate more diverse and realistic samples.
        Falls back to template generation if Gemini is unavailable.
        """
        if not self.use_gemini:
            # Fallback to template generation
            return self.generate_single_entity_samples(count)
        
        samples = []
        
        prompt_template = """Generate {count} realistic sentences containing PII (Personally Identifiable Information).

Requirements:
1. Include Indian PII types: Aadhaar numbers (12 digits like "1234 5678 9012"), PAN numbers (like "ABCDE1234F")
2. Include general PII: email addresses, phone numbers, person names
3. Use natural, conversational language
4. Include context words like "my aadhaar is", "email me at", "PAN card number"
5. Mix formal and informal styles

Output as JSON array with this format:
[
  {{
    "text": "My Aadhaar number is 2345 6789 0123 and email is user@example.com",
    "entities": [
      {{"type": "IN_AADHAAR", "value": "2345 6789 0123", "start": 21, "end": 35}},
      {{"type": "EMAIL_ADDRESS", "value": "user@example.com", "start": 50, "end": 66}}
    ]
  }}
]

Generate {count} diverse examples:"""
        
        prompt = prompt_template.format(count=min(count, 10))
        response = self._generate_with_gemini(prompt)
        
        if response:
            try:
                # Parse JSON from response
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    data = json.loads(json_match.group())
                    for item in data:
                        entities = [
                            DetectedEntity(**e) for e in item.get("entities", [])
                        ]
                        sample = TrainingSample(
                            text=item["text"],
                            entities=entities,
                            flagged=len(entities) > 0,
                            confidence=1.0,
                            reason=self._generate_reason(entities)
                        )
                        samples.append(sample)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing Gemini response: {e}")
        
        # Fill remaining with template generation
        remaining = count - len(samples)
        if remaining > 0:
            samples.extend(self.generate_single_entity_samples(remaining))
        
        return samples[:count]
    
    def _generate_reason(self, entities: List[DetectedEntity]) -> str:
        """Generate a human-readable reason for the detection."""
        if not entities:
            return "No PII detected"
        
        entity_counts = {}
        for e in entities:
            entity_counts[e.type] = entity_counts.get(e.type, 0) + 1
        
        reason_parts = []
        for etype, count in entity_counts.items():
            readable_name = etype.replace("_", " ").replace("IN ", "").title()
            reason_parts.append(f"{count} {readable_name}")
        
        return "Detected " + ", ".join(reason_parts)
    
    def verify_sample(self, sample: TrainingSample) -> Tuple[bool, List[str]]:
        """
        Verify a generated sample for correctness.
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Check entity positions
        for entity in sample.entities:
            # Verify the value exists at the specified position
            extracted = sample.text[entity.start:entity.end]
            if extracted != entity.value:
                issues.append(
                    f"Position mismatch for {entity.type}: "
                    f"expected '{entity.value}' at {entity.start}:{entity.end}, "
                    f"found '{extracted}'"
                )
            
            # Validate entity format
            is_valid, msg = validate_entity(entity.type, entity.value)
            if not is_valid:
                issues.append(f"Invalid {entity.type}: {msg}")
        
        # Check for overlapping entities
        sorted_entities = sorted(sample.entities, key=lambda e: e.start)
        for i in range(len(sorted_entities) - 1):
            if sorted_entities[i].end > sorted_entities[i + 1].start:
                issues.append(
                    f"Overlapping entities: {sorted_entities[i].type} and {sorted_entities[i + 1].type}"
                )
        
        return len(issues) == 0, issues
    
    def generate_dataset(
        self,
        total_samples: int = 10000,
        single_entity_ratio: float = 0.5,
        multi_entity_ratio: float = 0.2,
        negative_ratio: float = 0.2,
        edge_case_ratio: float = 0.1,
        verify: bool = True
    ) -> List[TrainingSample]:
        """
        Generate a complete dataset with specified distribution.
        
        Args:
            total_samples: Total number of samples to generate
            single_entity_ratio: Ratio of single-entity samples
            multi_entity_ratio: Ratio of multi-entity samples
            negative_ratio: Ratio of negative (no PII) samples
            edge_case_ratio: Ratio of edge case samples
            verify: Whether to verify samples
            
        Returns:
            List of training samples
        """
        # Calculate counts
        single_count = int(total_samples * single_entity_ratio)
        multi_count = int(total_samples * multi_entity_ratio)
        negative_count = int(total_samples * negative_ratio)
        edge_count = total_samples - single_count - multi_count - negative_count
        
        print(f"Generating {single_count} single-entity samples...")
        samples = self.generate_single_entity_samples(single_count)
        
        print(f"Generating {multi_count} multi-entity samples...")
        samples.extend(self.generate_multi_entity_samples(multi_count))
        
        print(f"Generating {negative_count} negative samples...")
        samples.extend(self.generate_negative_samples(negative_count))
        
        print(f"Generating {edge_count} edge case samples...")
        samples.extend(self.generate_edge_case_samples(edge_count))
        
        if verify:
            print("Verifying samples...")
            valid_samples = []
            invalid_count = 0
            
            for sample in samples:
                is_valid, issues = self.verify_sample(sample)
                if is_valid:
                    valid_samples.append(sample)
                else:
                    invalid_count += 1
                    # Try to regenerate invalid samples
                    if sample.flagged:
                        new_sample = self._generate_from_template(
                            random.choice(ALL_SINGLE_ENTITY_TEMPLATES)
                        )
                        is_valid, _ = self.verify_sample(new_sample)
                        if is_valid:
                            valid_samples.append(new_sample)
            
            print(f"Verified: {len(valid_samples)} valid, {invalid_count} regenerated")
            samples = valid_samples
        
        # Shuffle the dataset
        random.shuffle(samples)
        
        return samples


class TeacherVerifierLoop:
    """
    Implements a teacher-verifier loop using Gemini for quality assurance.
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        
        if self.gemini_api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.gemini_api_key)
            except ImportError:
                print("Warning: google-genai not installed")
    
    def verify_with_gemini(self, sample: TrainingSample) -> Tuple[bool, str, float]:
        """
        Use Gemini to verify a sample's annotations.
        
        Returns:
            Tuple of (is_correct, feedback, confidence)
        """
        if not self.client:
            return True, "Verification skipped (no Gemini client)", 1.0
        
        prompt = f"""Verify this PII detection result. Check if all entities are correctly identified with accurate positions.

Text: "{sample.text}"

Detected entities:
{json.dumps([e.to_dict() for e in sample.entities], indent=2)}

Respond with JSON:
{{
  "is_correct": true/false,
  "feedback": "explanation of any issues",
  "confidence": 0.0-1.0,
  "missed_entities": [],
  "false_positives": []
}}"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )
            
            result = json.loads(response.text)
            return (
                result.get("is_correct", True),
                result.get("feedback", ""),
                result.get("confidence", 1.0)
            )
        except Exception as e:
            print(f"Verification error: {e}")
            return True, f"Verification failed: {e}", 0.5
    
    def enhance_sample(self, sample: TrainingSample, feedback: str) -> TrainingSample:
        """
        Use feedback to enhance/correct a sample.
        """
        if not self.client:
            return sample
        
        prompt = f"""Fix this PII detection sample based on the feedback.

Original text: "{sample.text}"
Original entities: {json.dumps([e.to_dict() for e in sample.entities], indent=2)}
Feedback: {feedback}

Provide corrected JSON:
{{
  "text": "the text",
  "entities": [
    {{"type": "ENTITY_TYPE", "value": "value", "start": 0, "end": 5}}
  ]
}}"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                }
            )
            
            result = json.loads(response.text)
            entities = [DetectedEntity(**e) for e in result.get("entities", [])]
            
            return TrainingSample(
                text=result.get("text", sample.text),
                entities=entities,
                flagged=len(entities) > 0,
                confidence=1.0,
                reason=self._generate_reason(entities)
            )
        except Exception as e:
            print(f"Enhancement error: {e}")
            return sample
    
    def _generate_reason(self, entities: List[DetectedEntity]) -> str:
        if not entities:
            return "No PII detected"
        
        entity_counts = {}
        for e in entities:
            entity_counts[e.type] = entity_counts.get(e.type, 0) + 1
        
        reason_parts = []
        for etype, count in entity_counts.items():
            readable_name = etype.replace("_", " ").replace("IN ", "").title()
            reason_parts.append(f"{count} {readable_name}")
        
        return "Detected " + ", ".join(reason_parts)
    
    def run_verification_loop(
        self, 
        samples: List[TrainingSample],
        max_iterations: int = 2
    ) -> List[TrainingSample]:
        """
        Run the teacher-verifier loop on a set of samples.
        """
        verified_samples = []
        
        for sample in samples:
            current_sample = sample
            
            for iteration in range(max_iterations):
                is_correct, feedback, confidence = self.verify_with_gemini(current_sample)
                
                if is_correct and confidence >= 0.8:
                    current_sample.confidence = confidence
                    break
                elif feedback:
                    current_sample = self.enhance_sample(current_sample, feedback)
            
            verified_samples.append(current_sample)
        
        return verified_samples

