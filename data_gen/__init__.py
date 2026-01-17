"""
PII Synthetic Data Generation Module

This module provides tools for generating synthetic PII training data
using Gemini 1.5 Pro as a teacher model with verification loops.
"""

from .config import ENTITY_CONFIG, SEVERITY_SCORES
from .generator import PIIDataGenerator
from .templates import TEMPLATES
from .validators import validate_aadhaar, validate_pan
from .dataset_builder import DatasetBuilder

__all__ = [
    "ENTITY_CONFIG",
    "SEVERITY_SCORES", 
    "PIIDataGenerator",
    "TEMPLATES",
    "validate_aadhaar",
    "validate_pan",
    "DatasetBuilder",
]

