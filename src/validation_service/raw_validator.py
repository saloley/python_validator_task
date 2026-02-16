from pathlib import Path
from typing import Dict

from .base_validator import BaseValidator
from .validation_error import ValidationError
from .logger_config import logger


class RawValidator(BaseValidator):
    def validate_folder(self, folder_name: str) -> bool:
        logger.info(f"Starting RAW validation for folder: {folder_name}")
        
        # Check if folder exists
        if not self.validate_folder_exists(folder_name):
            return False
        
        # Check if folder has files
        if not self.validate_folder_has_files(folder_name):
            return False
        
        # Validate columns in each CSV file
        folder_path = self.base_path / folder_name
        csv_files = list(folder_path.glob('*.csv'))
        
        if not csv_files:
            error = ValidationError(
                error_level='info',
                error_text=f"No CSV files found in folder '{folder_name}'",
                folder_name=str(folder_path)
            )
            self.errors.append(error)
            logger.info(f"No CSV files in: {folder_path}")
            return True  # Not an error, just info
        
        logger.info(f"Found {len(csv_files)} CSV file(s) in {folder_name}")
        
        # Get required columns for this folder
        required_cols = self.required_columns.get(folder_name, {}).get('required_columns', [])
        
        if not required_cols:
            logger.warning(f"No required columns configured for folder: {folder_name}")
            return True
        
        # Validate each CSV file
        all_valid = True
        for csv_file in csv_files:
            is_valid = self.validate_csv_columns(
                csv_file,
                required_cols,
                folder_name
            )
            if not is_valid:
                all_valid = False
        
        return all_valid
    
    def validate_all_folders(self) -> bool:
        logger.info("Starting RAW validation for all folders")
       
        all_valid = True
        
        for folder_name in self.required_columns.keys():
            is_valid = self.validate_folder(folder_name)
            if not is_valid:
                all_valid = False
        
        logger.info("="*60)
        logger.info(f"RAW validation completed. Total errors: {len(self.errors)}")
        logger.info("="*60)
        
        return all_valid
