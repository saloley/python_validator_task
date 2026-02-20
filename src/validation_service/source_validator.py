import csv
from pathlib import Path
from typing import Dict, Any, List

from .base_validator import BaseValidator
from .validation_error import ValidationError
from .type_checker import is_null_value, validate_value_type
from .logger_config import logger


class SourceValidator(BaseValidator):
    CONFIG_SECTION = 'source_validation'

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
                logger.warning(f"No column config for {file_path.name}, skipping")
                return True

            with open(file_path, 'r', encoding=self.csv_encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter=self.csv_delimiter)

                if reader.fieldnames is None:
                    self.errors.append(ValidationError(
                        error_level='error',
                        error_text="File is empty (no header found)",
                        file_name=file_path.name,
                        folder_name=folder_name,
                        line_number=0
                    ))
                    logger.error(f"Empty file: {file_path}")
                    return False

                # Build normalized header map: normalized_name -> original_name
                normalized_header: Dict[str, str] = {
                    self._normalize_column_name(col): col
                    for col in reader.fieldnames
                }

                logger.debug(f"Header columns: {list(reader.fieldnames)}")

                # Step 1: check all expected columns exist
                all_columns_found = True
                for col_name in columns_config.keys():
                    if self._normalize_column_name(col_name) not in normalized_header:
                        self.errors.append(ValidationError(
                            error_level='error',
                            error_text=f"Required column '{col_name}' is missing",
                            file_name=file_path.name,
                            folder_name=folder_name,
                            line_number=0
                        ))
                        logger.error(f"Missing column '{col_name}' in {file_path.name}")
                        all_columns_found = False

                if not all_columns_found:
                    return False

                # Step 2: validate types and nullable row by row
                line_number = 1  # header = line 1, data starts at line 2
                validation_passed = True

                for row in reader:
                    line_number += 1

                    for col_name, col_spec in columns_config.items():
                        normalized_col = self._normalize_column_name(col_name)
                        original_col = normalized_header.get(normalized_col)

                        if original_col is None:
                            continue  # already reported as missing

                        value = row.get(original_col, '')
                        expected_type = col_spec.get('type', 'str')
                        nullable = col_spec.get('nullable', True)

                        if is_null_value(value):
                            if not nullable:
                                self.errors.append(ValidationError(
                                    error_level='error',
                                    error_text=f"Column '{col_name}' cannot be NULL",
                                    file_name=file_path.name,
                                    folder_name=folder_name,
                                    line_number=line_number,
                                    value_type=expected_type,
                                    value=value
                                ))
                                logger.error(
                                    f"NULL in non-nullable column '{col_name}' "
                                    f"at line {line_number} in {file_path.name}"
                                )
                                validation_passed = False
                            continue  # skip type check for null values

                        if not validate_value_type(value, expected_type):
                            self.errors.append(ValidationError(
                                error_level='error',
                                error_text=f"Wrong datatype for the column '{col_name}'",
                                file_name=file_path.name,
                                folder_name=folder_name,
                                line_number=line_number,
                                value_type=expected_type,
                                value=value
                            ))
                            logger.error(
                                f"Type mismatch in column '{col_name}' at line {line_number} "
                                f"in {file_path.name}: expected {expected_type}, got '{value}'"
                            )
                            validation_passed = False

                return validation_passed

        except UnicodeDecodeError as e:
            self.errors.append(ValidationError(
                error_level='error',
                error_text=f"Encoding error: {str(e)}",
                file_name=file_path.name,
                folder_name=folder_name,
                line_number=0
            ))
            logger.error(f"Encoding error in {file_path}: {e}")
            return False

        except Exception as e:
            self.errors.append(ValidationError(
                error_level='error',
                error_text=f"Error reading file: {str(e)}",
                file_name=file_path.name,
                folder_name=folder_name,
                line_number=0
            ))
            logger.error(f"Error reading {file_path}: {e}")
            return False

    def validate_single_subfolder(
        self,
        base_folder: str,
        subfolder_name: str,
        subfolder_config: Dict[str, Any]
    ) -> bool:
        logger.info(f"Validating SOURCE subfolder: {base_folder}/{subfolder_name}")

        folder_display_name = f"{base_folder}/{subfolder_name}"

        # RULE 1: folder exists — BaseValidator method
        if not self.validate_folder_exists(folder_display_name):
            return False

        # RULE 2: folder has at least one file — BaseValidator method
        if not self.validate_folder_has_files(folder_display_name):
            return False

        full_path = self.base_path / folder_display_name
        expected_files: Dict[str, Any] = subfolder_config.get('files', {})

        if not expected_files:
            logger.warning(f"No file specs in config for subfolder '{subfolder_name}', skipping")
            return True

        # RULE 3: warn about unexpected CSV files
        actual_csv_files = self.get_csv_files_in_folder(full_path)
        expected_file_names = set(expected_files.keys())

        for csv_file in actual_csv_files:
            if csv_file.name not in expected_file_names:
                self.errors.append(ValidationError(
                    error_level='warning',
                    error_text=f"Unexpected file '{csv_file.name}' found in folder",
                    file_name=csv_file.name,
                    folder_name=folder_display_name
                ))
                logger.warning(f"Unexpected file: {csv_file.name} in {full_path}")

        # RULE 4 & 5: check each expected file exists and validate it
        all_valid = True
        for file_name, file_config in expected_files.items():
            file_path = full_path / file_name

            if not file_path.exists():
                self.errors.append(ValidationError(
                    error_level='error',
                    error_text=f"Required file '{file_name}' is missing",
                    file_name=file_name,
                    folder_name=folder_display_name,
                    line_number=0
                ))
                logger.error(f"Missing expected file: {file_path}")
                all_valid = False
                continue

            is_valid = self.validate_source_file(file_path, file_config, folder_display_name)
            if not is_valid:
                all_valid = False

        return all_valid

    def validate_all_folders(self) -> bool:

        logger.info("Starting SOURCE validation for all subfolders")

        base_folder = self.get_base_folder_name(self.CONFIG_SECTION)
        config_subfolders = self.get_config_subfolders(self.CONFIG_SECTION)

        if not config_subfolders:
            logger.warning(f"No subfolders configured for '{self.CONFIG_SECTION}'")
            return True

        logger.info(f"Base folder: {base_folder}")
        logger.info(f"Subfolders to validate: {list(config_subfolders.keys())}")

        all_valid = True
        for subfolder_name, subfolder_config in config_subfolders.items():
            logger.info(f"\n--- Validating: {base_folder}/{subfolder_name} ---")

            is_valid = self.validate_single_subfolder(
                base_folder=base_folder,
                subfolder_name=subfolder_name,
                subfolder_config=subfolder_config
            )
            if not is_valid:
                all_valid = False

        summary = self.get_error_summary()
        logger.info("SOURCE validation completed")
        logger.info(f"Errors: {summary['error']}, Warnings: {summary['warning']}, Info: {summary['info']}")

        return all_valid