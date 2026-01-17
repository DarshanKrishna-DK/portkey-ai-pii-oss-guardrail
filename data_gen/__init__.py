"""
PII Synthetic Data Generation Module

This module provides tools for generating synthetic PII training data
with support for realistic noise, adversarial patterns, and dangerous negatives.

Key Components:
- config: Entity patterns, context words, generators
- templates: Context-rich sentence templates
- adversarial_templates: Evasion, OCR, informal patterns
- augmentation: Noise generators, character confusion
- robust_generator: Production-ready data generator
"""

from .config import ENTITY_CONFIG, SEVERITY_SCORES
from .generator import PIIDataGenerator
from .templates import TEMPLATES
from .validators import validate_aadhaar, validate_pan
from .dataset_builder import DatasetBuilder

# Robust generation (recommended for production)
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
    # Original exports
    "ENTITY_CONFIG",
    "SEVERITY_SCORES", 
    "PIIDataGenerator",
    "TEMPLATES",
    "validate_aadhaar",
    "validate_pan",
    "DatasetBuilder",
    
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

