from pathlib import Path
from typing import Dict, List

from .base_validator import BaseValidator
from .validation_error import ValidationError
from .logger_config import logger


class RawValidator(BaseValidator):
    CONFIG_SECTION = 'raw_validation'

    def get_config_subfolders(self, config_section: str) -> Dict[str, List[str]]:
        section = self.required_columns.get(config_section, {})
        subfolders = section.get('subfolders', {})

        result = {}
        for folder_name, folder_data in subfolders.items():
            result[folder_name] = folder_data.get('required_columns', [])

        return result

    def validate_single_subfolder(
            self,
            base_folder: str,
            subfolder_name: str,
            required_columns: List[str]
    ) -> bool:

        logger.info(f"Validating RAW subfolder: {base_folder}/{subfolder_name}")

        folder_display_name = f"{base_folder}/{subfolder_name}"

        # RULE 1: use BaseValidator method instead of manual check
        if not self.validate_folder_exists(folder_display_name):
            return False

        # RULE 2: use BaseValidator method instead of manual check
        if not self.validate_folder_has_files(folder_display_name):
            return False

        # RULE 3: validate required columns in each CSV file
        full_path = self.base_path / folder_display_name
        csv_files = self.get_csv_files_in_folder(full_path)

        if not csv_files:
            info = ValidationError(
                error_level='info',
                error_text=f"No CSV files found in folder '{subfolder_name}'",
                folder_name=folder_display_name,
                file_name='',
                line_number=0
            )
            self.errors.append(info)
            logger.info(f"No CSV files in: {full_path}")
            return True

        logger.info(f"Found {len(csv_files)} CSV file(s) in {subfolder_name}")

        all_valid = True
        for csv_file in csv_files:
            is_valid = self.validate_csv_columns(
                file_path=csv_file,
                required_columns=required_columns,
                folder_name=folder_display_name
            )
            if not is_valid:
                all_valid = False

        return all_valid

    def validate_all_folders(self) -> bool:

        base_folder = self.get_base_folder_name(self.CONFIG_SECTION)
        config_subfolders = self.get_config_subfolders(self.CONFIG_SECTION)

        if not config_subfolders:
            logger.warning(f"No subfolders configured for '{self.CONFIG_SECTION}'")
            return True

        logger.info(f"Base folder: {base_folder}")
        logger.info(f"Subfolders to validate: {list(config_subfolders.keys())}")

        all_valid = True
        for subfolder_name, required_columns in config_subfolders.items():
            logger.info(f"\n--- Validating: {base_folder}/{subfolder_name} ---")
            logger.info(f"Required columns: {required_columns}")

            is_valid = self.validate_single_subfolder(
                base_folder=base_folder,
                subfolder_name=subfolder_name,
                required_columns=required_columns
            )
            if not is_valid:
                all_valid = False

        summary = self.get_error_summary()
        logger.info(f"Errors: {summary['error']}, Warnings: {summary['warning']}, Info: {summary['info']}")


        return all_valid