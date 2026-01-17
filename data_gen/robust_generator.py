"""
Robust PII Data Generator

An enhanced generator that produces realistic, messy, and adversarial PII examples
for training models that perform well in production environments.

Key features:
- Confidence-aware labeling (strong → weak → ambiguous)
- Noise/corruption at multiple levels
- Dangerous negatives (false positive traps)
- Adversarial evasion patterns
- Realistic OCR/scan artifacts
- Multi-language support (Hinglish)
"""

import os
import re
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from .config import ENTITY_CONFIG, SEVERITY_SCORES, get_generator
from .templates import (
    TEMPLATES, ALL_SINGLE_ENTITY_TEMPLATES,
    MULTI_ENTITY_TEMPLATES, NEGATIVE_TEMPLATES
)
from .adversarial_templates import (
    ALL_ADVERSARIAL_TEMPLATES, ALL_DANGEROUS_NEGATIVES,
    EVASION_TEMPLATES, OCR_ARTIFACT_TEMPLATES,
    INFORMAL_TEMPLATES, HINGLISH_TEMPLATES,
    AMBIGUOUS_POSITIVE_TEMPLATES, MULTI_PII_NOISY_TEMPLATES,
    get_template_by_difficulty
)
from .augmentation import (
    augment_pii_value, generate_dangerous_negative,
    NoiseLevel, AugmentedValue,
    apply_ocr_noise, apply_typo, apply_case_noise
)
from .validators import validate_entity


class SampleDifficulty(Enum):
    """Difficulty level of a training sample."""
    EASY = "easy"           # Clean, canonical, high confidence
    MEDIUM = "medium"       # Some noise, moderate confidence
    HARD = "hard"           # Significant noise, lower confidence
    ADVERSARIAL = "adversarial"  # Evasion attempts, very low confidence
    NEGATIVE = "negative"   # No PII (clean negative)
    DANGEROUS_NEGATIVE = "dangerous_negative"  # Looks like PII but isn't


@dataclass
class RobustTrainingSample:
    """
    An enhanced training sample with confidence and difficulty metadata.
    """
    text: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    flagged: bool = False
    confidence: float = 1.0
    severity: int = 0
    reason: str = ""
    difficulty: str = "easy"
    noise_level: str = "none"
    augmentation_types: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entities": self.entities,
            "flagged": self.flagged,
            "confidence": self.confidence,
            "severity": self.severity,
            "reason": self.reason,
            "difficulty": self.difficulty,
            "noise_level": self.noise_level,
        }
    
    def to_training_format(self) -> Dict[str, Any]:
        """Convert to instruction-tuned training format."""
        output = {
            "flagged": self.flagged,
            "entities": self.entities,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
        }
        
        return {
            "conversations": [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f'Detect PII in: "{self.text}"'
                },
                {
                    "role": "assistant",
                    "content": json.dumps(output, indent=2)
                }
            ]
        }
    
    def _get_system_prompt(self) -> str:
        return """You are a PII detection model. Analyze text and identify PII entities with their exact positions.

Output JSON with: flagged (bool), entities (array with type, value, start, end), confidence (0-1), reason (string).

Entity types: IN_AADHAAR, IN_PAN, EMAIL_ADDRESS, PHONE_NUMBER, PERSON, US_SSN, CREDIT_CARD

Important: 
- Report confidence based on how clear/corrupted the PII appears
- Handle typos, OCR errors, and obfuscation attempts
- Don't flag non-PII identifiers like order IDs, product codes, or dates"""


class RobustPIIGenerator:
    """
    Enhanced PII generator for production-ready training data.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator."""
        if seed is not None:
            random.seed(seed)
        
        # Distribution weights for sample types
        self.distribution = {
            SampleDifficulty.EASY: 0.25,           # 25% clean samples
            SampleDifficulty.MEDIUM: 0.25,         # 25% medium noise
            SampleDifficulty.HARD: 0.15,           # 15% hard samples
            SampleDifficulty.ADVERSARIAL: 0.10,   # 10% adversarial
            SampleDifficulty.NEGATIVE: 0.10,       # 10% clean negatives
            SampleDifficulty.DANGEROUS_NEGATIVE: 0.15,  # 15% dangerous negatives
        }
    
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
    
    def _generate_clean_sample(self, template: str) -> RobustTrainingSample:
        """Generate a clean, canonical sample."""
        text = template
        entities = []
        augmentation_types = []
        
        # Find and replace placeholders
        placeholders = re.findall(r'\{([A-Z_]+)\}', template)
        
        for placeholder in placeholders:
            if placeholder in ENTITY_CONFIG:
                generator = get_generator(placeholder)
                value = generator()
                
                # Find position and replace
                placeholder_str = f"{{{placeholder}}}"
                if placeholder_str in text:
                    start = text.find(placeholder_str)
                    text = text.replace(placeholder_str, value, 1)
                    end = start + len(value)
                    
                    entities.append({
                        "type": placeholder,
                        "value": value,
                        "start": start,
                        "end": end
                    })
                    augmentation_types.append("clean")
        
        # Recalculate positions
        final_entities = []
        for entity in entities:
            positions = self._find_entity_positions(text, entity["value"])
            if positions:
                start, end = positions[0]
                final_entities.append({
                    "type": entity["type"],
                    "value": entity["value"],
                    "start": start,
                    "end": end
                })
        
        final_entities.sort(key=lambda e: e["start"])
        
        return RobustTrainingSample(
            text=text,
            entities=final_entities,
            flagged=len(final_entities) > 0,
            confidence=0.95,
            severity=max((SEVERITY_SCORES.get(e["type"], 5) for e in final_entities), default=0),
            reason=self._generate_reason(final_entities),
            difficulty="easy",
            noise_level="none",
            augmentation_types=augmentation_types
        )
    
    def _generate_augmented_sample(
        self, 
        template: str, 
        noise_level: NoiseLevel
    ) -> RobustTrainingSample:
        """Generate a sample with augmentation/noise."""
        text = template
        entities = []
        augmentation_types = []
        confidences = []
        
        # Find and replace placeholders with augmented values
        placeholders = re.findall(r'\{([A-Z_]+)\}', template)
        
        for placeholder in placeholders:
            if placeholder in ENTITY_CONFIG:
                generator = get_generator(placeholder)
                original_value = generator()
                
                # Apply augmentation
                augmented = augment_pii_value(placeholder, original_value)
                value = augmented.augmented
                confidences.append(augmented.confidence)
                augmentation_types.append(augmented.augmentation_type)
                
                # Find position and replace
                placeholder_str = f"{{{placeholder}}}"
                if placeholder_str in text:
                    start = text.find(placeholder_str)
                    text = text.replace(placeholder_str, value, 1)
                    end = start + len(value)
                    
                    entities.append({
                        "type": placeholder,
                        "value": value,
                        "start": start,
                        "end": end
                    })
        
        # Apply additional text-level noise based on noise level
        if noise_level == NoiseLevel.MEDIUM:
            if random.random() < 0.3:
                text = apply_case_noise(text)
        elif noise_level == NoiseLevel.HEAVY:
            if random.random() < 0.2:
                # Apply light OCR noise to surrounding text (not entities)
                text = apply_typo(text, intensity=0.02)
        
        # Recalculate positions after all modifications
        final_entities = []
        for entity in entities:
            # Try to find the value in the modified text
            positions = self._find_entity_positions(text, entity["value"])
            if positions:
                start, end = positions[0]
                final_entities.append({
                    "type": entity["type"],
                    "value": entity["value"],
                    "start": start,
                    "end": end
                })
        
        final_entities.sort(key=lambda e: e["start"])
        
        # Calculate overall confidence
        overall_confidence = min(confidences) if confidences else 0.5
        
        # Map noise level to difficulty
        difficulty_map = {
            NoiseLevel.NONE: "easy",
            NoiseLevel.LIGHT: "easy",
            NoiseLevel.MEDIUM: "medium",
            NoiseLevel.HEAVY: "hard",
            NoiseLevel.ADVERSARIAL: "adversarial",
        }
        
        return RobustTrainingSample(
            text=text,
            entities=final_entities,
            flagged=len(final_entities) > 0,
            confidence=overall_confidence,
            severity=max((SEVERITY_SCORES.get(e["type"], 5) for e in final_entities), default=0),
            reason=self._generate_reason(final_entities, overall_confidence),
            difficulty=difficulty_map.get(noise_level, "medium"),
            noise_level=noise_level.name.lower(),
            augmentation_types=augmentation_types
        )
    
    def _generate_dangerous_negative(self) -> RobustTrainingSample:
        """Generate a dangerous negative (looks like PII but isn't)."""
        text, label = generate_dangerous_negative()
        
        return RobustTrainingSample(
            text=text,
            entities=[],
            flagged=False,
            confidence=0.90,  # High confidence it's NOT PII
            severity=0,
            reason="No PII detected - identifier is not sensitive personal information",
            difficulty="dangerous_negative",
            noise_level="none",
            augmentation_types=["dangerous_negative"]
        )
    
    def _generate_clean_negative(self) -> RobustTrainingSample:
        """Generate a clean negative sample."""
        text = random.choice(NEGATIVE_TEMPLATES)
        
        return RobustTrainingSample(
            text=text,
            entities=[],
            flagged=False,
            confidence=0.95,
            severity=0,
            reason="No PII detected",
            difficulty="negative",
            noise_level="none",
            augmentation_types=["clean_negative"]
        )
    
    def _generate_reason(
        self, 
        entities: List[Dict], 
        confidence: float = 1.0
    ) -> str:
        """Generate a human-readable reason."""
        if not entities:
            return "No PII detected"
        
        entity_counts = {}
        for e in entities:
            entity_counts[e["type"]] = entity_counts.get(e["type"], 0) + 1
        
        reason_parts = []
        for etype, count in sorted(entity_counts.items()):
            readable = etype.replace("_", " ").replace("IN ", "").title()
            reason_parts.append(f"{count} {readable}")
        
        detected_str = ", ".join(reason_parts)
        
        if confidence < 0.6:
            return f"Possibly detected {detected_str} (low confidence due to noise/corruption)"
        elif confidence < 0.8:
            return f"Likely detected {detected_str} (moderate confidence)"
        else:
            return f"Detected {detected_str}"
    
    def generate_easy_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate clean, canonical samples."""
        samples = []
        templates = ALL_SINGLE_ENTITY_TEMPLATES + MULTI_ENTITY_TEMPLATES
        
        for _ in range(count):
            template = random.choice(templates)
            sample = self._generate_clean_sample(template)
            samples.append(sample)
        
        return samples
    
    def generate_medium_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate samples with medium noise."""
        samples = []
        templates = (
            ALL_SINGLE_ENTITY_TEMPLATES + 
            INFORMAL_TEMPLATES + 
            OCR_ARTIFACT_TEMPLATES
        )
        
        for _ in range(count):
            template = random.choice(templates)
            sample = self._generate_augmented_sample(template, NoiseLevel.MEDIUM)
            samples.append(sample)
        
        return samples
    
    def generate_hard_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate samples with heavy noise."""
        samples = []
        templates = (
            AMBIGUOUS_POSITIVE_TEMPLATES + 
            HINGLISH_TEMPLATES +
            MULTI_PII_NOISY_TEMPLATES
        )
        
        for _ in range(count):
            template = random.choice(templates)
            sample = self._generate_augmented_sample(template, NoiseLevel.HEAVY)
            samples.append(sample)
        
        return samples
    
    def generate_adversarial_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate adversarial evasion samples."""
        samples = []
        
        for _ in range(count):
            template = random.choice(EVASION_TEMPLATES)
            sample = self._generate_augmented_sample(template, NoiseLevel.ADVERSARIAL)
            samples.append(sample)
        
        return samples
    
    def generate_negative_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate clean negative samples."""
        return [self._generate_clean_negative() for _ in range(count)]
    
    def generate_dangerous_negative_samples(self, count: int) -> List[RobustTrainingSample]:
        """Generate dangerous negative samples."""
        samples = []
        
        # Mix generated dangerous negatives with template-based ones
        for _ in range(count):
            if random.random() < 0.5:
                sample = self._generate_dangerous_negative()
            else:
                text = random.choice(ALL_DANGEROUS_NEGATIVES)
                sample = RobustTrainingSample(
                    text=text,
                    entities=[],
                    flagged=False,
                    confidence=0.85,
                    severity=0,
                    reason="No PII detected - pattern resembles but is not sensitive data",
                    difficulty="dangerous_negative",
                    noise_level="none",
                    augmentation_types=["template_dangerous_negative"]
                )
            samples.append(sample)
        
        return samples
    
    def generate_dataset(
        self,
        total_samples: int = 10000,
        distribution: Optional[Dict[SampleDifficulty, float]] = None
    ) -> List[RobustTrainingSample]:
        """
        Generate a complete robust dataset.
        
        Args:
            total_samples: Total number of samples
            distribution: Optional custom distribution of sample types
        
        Returns:
            List of RobustTrainingSample objects
        """
        dist = distribution or self.distribution
        
        # Calculate counts for each type
        counts = {
            difficulty: int(total_samples * ratio)
            for difficulty, ratio in dist.items()
        }
        
        # Adjust for rounding
        total_counted = sum(counts.values())
        if total_counted < total_samples:
            counts[SampleDifficulty.EASY] += total_samples - total_counted
        
        samples = []
        
        print(f"Generating {counts[SampleDifficulty.EASY]} easy samples...")
        samples.extend(self.generate_easy_samples(counts[SampleDifficulty.EASY]))
        
        print(f"Generating {counts[SampleDifficulty.MEDIUM]} medium samples...")
        samples.extend(self.generate_medium_samples(counts[SampleDifficulty.MEDIUM]))
        
        print(f"Generating {counts[SampleDifficulty.HARD]} hard samples...")
        samples.extend(self.generate_hard_samples(counts[SampleDifficulty.HARD]))
        
        print(f"Generating {counts[SampleDifficulty.ADVERSARIAL]} adversarial samples...")
        samples.extend(self.generate_adversarial_samples(counts[SampleDifficulty.ADVERSARIAL]))
        
        print(f"Generating {counts[SampleDifficulty.NEGATIVE]} clean negative samples...")
        samples.extend(self.generate_negative_samples(counts[SampleDifficulty.NEGATIVE]))
        
        print(f"Generating {counts[SampleDifficulty.DANGEROUS_NEGATIVE]} dangerous negative samples...")
        samples.extend(self.generate_dangerous_negative_samples(counts[SampleDifficulty.DANGEROUS_NEGATIVE]))
        
        # Shuffle
        random.shuffle(samples)
        
        # Print statistics
        self._print_stats(samples)
        
        return samples
    
    def _print_stats(self, samples: List[RobustTrainingSample]):
        """Print dataset statistics."""
        print("\n" + "=" * 60)
        print("DATASET STATISTICS")
        print("=" * 60)
        
        # Difficulty distribution
        difficulty_counts = {}
        for s in samples:
            difficulty_counts[s.difficulty] = difficulty_counts.get(s.difficulty, 0) + 1
        
        print("\nDifficulty Distribution:")
        for diff, count in sorted(difficulty_counts.items()):
            pct = 100 * count / len(samples)
            print(f"  {diff}: {count} ({pct:.1f}%)")
        
        # Confidence distribution
        conf_buckets = {"high (>0.8)": 0, "medium (0.6-0.8)": 0, "low (<0.6)": 0}
        for s in samples:
            if s.confidence > 0.8:
                conf_buckets["high (>0.8)"] += 1
            elif s.confidence >= 0.6:
                conf_buckets["medium (0.6-0.8)"] += 1
            else:
                conf_buckets["low (<0.6)"] += 1
        
        print("\nConfidence Distribution:")
        for bucket, count in conf_buckets.items():
            pct = 100 * count / len(samples)
            print(f"  {bucket}: {count} ({pct:.1f}%)")
        
        # Flagged vs not flagged
        flagged = sum(1 for s in samples if s.flagged)
        not_flagged = len(samples) - flagged
        print(f"\nFlagged: {flagged} ({100*flagged/len(samples):.1f}%)")
        print(f"Not Flagged: {not_flagged} ({100*not_flagged/len(samples):.1f}%)")
        
        # Entity type distribution
        entity_counts = {}
        for s in samples:
            for e in s.entities:
                entity_counts[e["type"]] = entity_counts.get(e["type"], 0) + 1
        
        print("\nEntity Type Distribution:")
        for etype, count in sorted(entity_counts.items()):
            print(f"  {etype}: {count}")
        
        print("=" * 60)


def build_robust_dataset(
    output_dir: str = "data",
    total_samples: int = 10000,
    eval_ratio: float = 0.2,
    seed: int = 42
) -> Tuple[str, str]:
    """
    Build and save a robust training dataset.
    
    Args:
        output_dir: Output directory
        total_samples: Total samples to generate
        eval_ratio: Ratio for evaluation set
        seed: Random seed
    
    Returns:
        Tuple of (train_path, eval_path)
    """
    import os
    from pathlib import Path
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    generator = RobustPIIGenerator(seed=seed)
    samples = generator.generate_dataset(total_samples)
    
    # Split
    random.shuffle(samples)
    split_idx = int(len(samples) * (1 - eval_ratio))
    train_samples = samples[:split_idx]
    eval_samples = samples[split_idx:]
    
    # Save
    train_path = os.path.join(output_dir, "train_robust.jsonl")
    eval_path = os.path.join(output_dir, "eval_robust.jsonl")
    
    print(f"\nSaving {len(train_samples)} training samples to {train_path}")
    with open(train_path, 'w', encoding='utf-8') as f:
        for sample in train_samples:
            f.write(json.dumps(sample.to_training_format(), ensure_ascii=False) + '\n')
    
    print(f"Saving {len(eval_samples)} evaluation samples to {eval_path}")
    with open(eval_path, 'w', encoding='utf-8') as f:
        for sample in eval_samples:
            f.write(json.dumps(sample.to_training_format(), ensure_ascii=False) + '\n')
    
    # Save metadata
    metadata = {
        "total_samples": len(samples),
        "train_samples": len(train_samples),
        "eval_samples": len(eval_samples),
        "seed": seed,
        "distribution": {
            d.value: sum(1 for s in samples if s.difficulty == d.value)
            for d in SampleDifficulty
        }
    }
    
    metadata_path = os.path.join(output_dir, "dataset_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nDataset saved!")
    print(f"  Train: {train_path}")
    print(f"  Eval: {eval_path}")
    print(f"  Metadata: {metadata_path}")
    
    return train_path, eval_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate robust PII training data")
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--output", type=str, default="data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-ratio", type=float, default=0.2)
    
    args = parser.parse_args()
    
    build_robust_dataset(
        output_dir=args.output,
        total_samples=args.samples,
        eval_ratio=args.eval_ratio,
        seed=args.seed
    )

