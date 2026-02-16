"""
File Validation Service

Modular validation service for CSV files with support for:
- RAW validation: folder structure and required columns
- SOURCE validation: file schemas, data types, nullable constraints
"""

__version__ = "0.2.0"
__author__ = "Your Name"

from .logger_config import logger
from .validation_error import ValidationError
from .base_validator import BaseValidator
from .raw_validator import RawValidator
from .source_validator import SourceValidator

__all__ = [
    "logger",
    "ValidationError",
    "BaseValidator",
    "RawValidator",
    "SourceValidator"
]
