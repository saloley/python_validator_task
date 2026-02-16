import csv
from pathlib import Path
from typing import Dict, Any

from .base_validator import BaseValidator
from .validation_error import ValidationError
from .type_checker import is_null_value, validate_value_type
from .logger_config import logger


class SourceValidator(BaseValidator):

    def validate_source_file(
        self,
        file_path: Path,
        file_config: Dict[str, Any],
        folder_name: str
    ) -> bool:
        try:
            logger.debug(f"Validating SOURCE file: {file_path}")
            
            columns_config = file_config.get('columns', {})
            if not columns_config:
                logger.warning(f"No column config for {file_path.name}")
                return True
            
            with open(file_path, 'r', encoding=self.csv_encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter=self.csv_delimiter)
                
                # Check header exists
                if reader.fieldnames is None:
                    error = ValidationError(
                        error_level='error',
                        error_text="File is empty (no header found)",
                        file_name=file_path.name,
                        folder_name=folder_name,
                        line_number=0
                    )
                    self.errors.append(error)
                    logger.error(f"Empty file: {file_path}")
                    return False
                
                # Normalize header
                header = reader.fieldnames
                normalized_header = {self._normalize_column_name(col): col 
                                    for col in header}
                
                logger.debug(f"Header columns: {header}")
                
                # Step 1: Validate required columns exist
                all_columns_found = True
                for col_name in columns_config.keys():
                    normalized_col = self._normalize_column_name(col_name)
                    
                    if normalized_col not in normalized_header:
                        error = ValidationError(
                            error_level='error',
                            error_text=f"Required column '{col_name}' is missing",
                            file_name=file_path.name,
                            folder_name=folder_name,
                            line_number=0
                        )
                        self.errors.append(error)
                        logger.error(f"Missing column '{col_name}' in {file_path.name}")
                        all_columns_found = False
                
                if not all_columns_found:
                    return False
                
                # Step 2: Validate data types and nullable for each row
                line_number = 1  # Header is line 1, data starts at line 2
                validation_passed = True
                
                for row in reader:
                    line_number += 1
                    
                    for col_name, col_spec in columns_config.items():
                        normalized_col = self._normalize_column_name(col_name)
                        original_col = normalized_header.get(normalized_col)
                        
                        if original_col is None:
                            continue  # Column missing, already reported
                        
                        value = row.get(original_col, '')
                        expected_type = col_spec.get('type', 'str')
                        nullable = col_spec.get('nullable', True)
                        
                        # Check if value is NULL
                        if is_null_value(value):
                            # If nullable=False, this is an error
                            if not nullable:
                                error = ValidationError(
                                    error_level='error',
                                    error_text=f"Column '{col_name}' cannot be NULL",
                                    file_name=file_path.name,
                                    folder_name=folder_name,
                                    line_number=line_number,
                                    value_type=expected_type,
                                    value=value
                                )
                                self.errors.append(error)
                                logger.error(
                                    f"NULL value in non-nullable column '{col_name}' "
                                    f"at line {line_number} in {file_path.name}"
                                )
                                validation_passed = False
                            # If nullable=True, skip type validation
                            continue
                        
                        # Validate data type (only if value is not NULL)
                        if not validate_value_type(value, expected_type):
                            error = ValidationError(
                                error_level='error',
                                error_text=f"Wrong datatype for the column '{col_name}'",
                                file_name=file_path.name,
                                folder_name=folder_name,
                                line_number=line_number,
                                value_type=expected_type,
                                value=value
                            )
                            self.errors.append(error)
                            logger.error(
                                f"Type mismatch in column '{col_name}' at line {line_number} "
                                f"in {file_path.name}: expected {expected_type}, got '{value}'"
                            )
                            validation_passed = False
                
                return validation_passed
                
        except UnicodeDecodeError as e:
            error = ValidationError(
                error_level='error',
                error_text=f"Encoding error: {str(e)}",
                file_name=file_path.name,
                folder_name=folder_name,
                line_number=0
            )
            self.errors.append(error)
            logger.error(f"Encoding error in {file_path}: {e}")
            return False
            
        except Exception as e:
            error = ValidationError(
                error_level='error',
                error_text=f"Error reading file: {str(e)}",
                file_name=file_path.name,
                folder_name=folder_name,
                line_number=0
            )
            self.errors.append(error)
            logger.error(f"Error reading {file_path}: {e}")
            return False
    
    def validate_source_folder(self, folder_name: str) -> bool:
        logger.info(f"Starting SOURCE validation for folder: {folder_name}")
        
        # Step 1: Check if folder exists
        if not self.validate_folder_exists(folder_name):
            return False
        
        # Step 2: Check if folder has files
        if not self.validate_folder_has_files(folder_name):
            return False
        
        folder_path = self.base_path / folder_name
        
        # Get expected files from config
        folder_config = self.required_columns.get(folder_name, {})
        expected_files = folder_config.get('files', {})
        
        if not expected_files:
            logger.warning(f"No file specifications in config for folder: {folder_name}")
            return True
        
        logger.info(f"Expected files in '{folder_name}': {list(expected_files.keys())}")
        
        # Step 3: Check all expected files exist
        all_valid = True
        for expected_file_name in expected_files.keys():
            expected_file_path = folder_path / expected_file_name
            
            if not expected_file_path.exists():
                error = ValidationError(
                    error_level='error',
                    error_text=f"Required file '{expected_file_name}' is missing",
                    folder_name=str(folder_path)
                )
                self.errors.append(error)
                logger.error(f"Missing file: {expected_file_path}")
                all_valid = False
        
        # Step 4: Check for unexpected files (warning only, don't validate them)
        actual_csv_files = list(folder_path.glob('*.csv'))
        expected_file_names = set(expected_files.keys())
        
        for csv_file in actual_csv_files:
            if csv_file.name not in expected_file_names:
                error = ValidationError(
                    error_level='warning',
                    error_text=f"Unexpected file '{csv_file.name}' found in folder",
                    file_name=csv_file.name,
                    folder_name=str(folder_path)
                )
                self.errors.append(error)
                logger.warning(f"Unexpected file: {csv_file.name} in {folder_path}")
        
        # Step 5: Validate ONLY expected files
        for file_name, file_config in expected_files.items():
            file_path = folder_path / file_name
            
            if not file_path.exists():
                continue  # Already reported as error
            
            is_valid = self.validate_source_file(file_path, file_config, folder_name)
            if not is_valid:
                all_valid = False
        
        return all_valid
    
    def validate_all_folders(self) -> bool:

        logger.info("Starting SOURCE validation for all folders")
       
        all_valid = True
        
        for folder_name in self.required_columns.keys():
            # Only validate folders that have 'files' key (SOURCE style)
            folder_config = self.required_columns.get(folder_name, {})
            if 'files' in folder_config:
                is_valid = self.validate_source_folder(folder_name)
                if not is_valid:
                    all_valid = False
            else:
                logger.warning(
                    f"Folder '{folder_name}' has no 'files' config, skipping SOURCE validation"
                )
        
        logger.info("="*60)
        logger.info(f"SOURCE validation completed. Total errors: {len(self.errors)}")
        logger.info("="*60)
        
        return all_valid
