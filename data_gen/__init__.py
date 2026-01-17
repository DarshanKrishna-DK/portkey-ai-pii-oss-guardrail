"""
PII Synthetic Data Generation Module v2

This module provides tools for generating synthetic PII training data
with support for realistic noise, adversarial patterns, and dangerous negatives.

Key Components:
- augmentation: Noise generators, character confusion, PII augmenters
- adversarial_templates: Evasion, OCR, informal patterns, dangerous negatives
- robust_generator: Production-ready data generator with difficulty levels
"""

from .robust_generator import (
    RobustPIIGenerator,
    RobustTrainingSample,
    SampleDifficulty,
    build_robust_dataset,
)
from .augmentation import (
    augment_pii_value,
    generate_dangerous_negative,
    NoiseLevel,
    AugmentedValue,
    AadhaarAugmenter,
    PANAugmenter,
    EmailAugmenter,
    PhoneAugmenter,
)
from .adversarial_templates import (
    ALL_ADVERSARIAL_TEMPLATES,
    ALL_DANGEROUS_NEGATIVES,
    get_template_by_difficulty,
)

__all__ = [
    # Robust generation
    "RobustPIIGenerator",
    "RobustTrainingSample",
    "SampleDifficulty",
    "build_robust_dataset",
    
    # Augmentation
    "augment_pii_value",
    "generate_dangerous_negative",
    "NoiseLevel",
    "AugmentedValue",
    "AadhaarAugmenter",
    "PANAugmenter",
    "EmailAugmenter",
    "PhoneAugmenter",
    
    # Adversarial templates
    "ALL_ADVERSARIAL_TEMPLATES",
    "ALL_DANGEROUS_NEGATIVES",
    "get_template_by_difficulty",
]
