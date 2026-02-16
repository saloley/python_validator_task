from pydantic import BaseModel, EmailStr, HttpUrl
from pydantic_core import ValidationError as PydanticValidationError
from datetime import datetime
from typing import Any, Type
import logging
from .logger_config import logger

def is_null_value(value: str) -> bool:
    if not value:
        return True
    
    value_stripped = value.strip()
    if not value_stripped:
        return True
    
    null_strings = ['null', 'none', 'n/a', 'na']
    if value_stripped.lower() in null_strings:
        return True
    
    return False


def validate_value_type(value: str, expected_type: str) -> bool:
    if not value or not value.strip():
        return True  # Empty values handled by nullable check
    
    value = value.strip()
    
    # here mapping dict so add types here
    type_mapping: dict[str, Type[Any]] = {
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'datetime': datetime,
        'email': EmailStr,      
        'url': HttpUrl,         
    }
    
    # get types from config
    python_type = type_mapping.get(expected_type.lower())
    
    if python_type is None:
        # if no type support True so skip
        logger.warning(f"Unknown type '{expected_type}', treating as valid string")
        return True  
    
    # custom support for bool
    if expected_type.lower() == 'bool':
        bool_values = {
            'true': True, 'false': False,
            '1': True, '0': False,
            'yes': True, 'no': False,
            'y': True, 'n': False,
            't': True, 'f': False
        }
        return value.lower() in bool_values
    

    try:

        class DynamicModel(BaseModel):
            value: python_type  
        

        DynamicModel(value=value)
        return True
        
    except PydanticValidationError as e:
        logger.debug(f"Type validation failed for '{value}' as {expected_type}: {e}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error validating '{value}' as {expected_type}: {e}")
        return False