import os
import csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

from .logger_config import logger

# Load environment variables
load_dotenv()


class ValidationError:

    def __init__(
        self,
        error_level: str,
        error_text: str,
        file_name: str = "",
        folder_name: str = "",
        line_number: int = 0
    ):

        self.error_level = error_level
        self.error_text = error_text
        self.file_name = file_name
        self.folder_name = folder_name
        self.line_number = line_number
    
    def to_dict(self) -> Dict[str, any]:
        # converting to dict for csv export
        return {
            'error_level': self.error_level,
            'error_text': self.error_text,
            'file_name': self.file_name,
            'folder_name': self.folder_name,
            'line_number': self.line_number
        }


class FileValidator:

    def __init__(
        self,
        base_path: str,
        required_columns_config: Dict[str, List[str]],
        csv_delimiter: str = ',',
        csv_encoding: str = 'utf-8'
    ):

        self.base_path = Path(base_path)
        self.required_columns = required_columns_config
        self.csv_delimiter = csv_delimiter
        self.csv_encoding = csv_encoding
        self.errors: List[ValidationError] = []
        
        logger.info(f"FileValidator initialized with base_path: {self.base_path}")
        logger.debug(f"Required columns config: {self.required_columns}")
    
    def _normalize_column_name(self, column: str) -> str:

        return column.strip().lower()
    
    def validate_folder_exists(self, folder_name: str) -> bool:

        folder_path = self.base_path / folder_name
        
        if not folder_path.exists():
            error = ValidationError(
                error_level='error',
                error_text=f"Required folder '{folder_name}' is missing",
                folder_name=str(folder_path)
            )
            self.errors.append(error)
            logger.error(f"Folder not found: {folder_path}")
            return False
        
        logger.info(f"Folder exists: {folder_path}")
        return True
    
    def validate_folder_has_files(self, folder_name: str) -> bool:

        folder_path = self.base_path / folder_name
        
        if not folder_path.exists():
            return False
        
        # Get all files (not directories) in the folder
        files = [f for f in folder_path.iterdir() if f.is_file()]
        
        if not files:
            error = ValidationError(
                error_level='warning',
                error_text=f"Folder '{folder_name}' does not contain any file",
                folder_name=str(folder_path)
            )
            self.errors.append(error)
            logger.warning(f"Empty folder: {folder_path}")
            return False
        
        logger.info(f"Folder contains {len(files)} file(s): {folder_path}")
        return True
    
    def validate_csv_columns(
        self,
        file_path: Path,
        required_columns: List[str],
        folder_name: str
    ) -> bool:

        try:
            logger.debug(f"Validating CSV columns in: {file_path}")
            
            with open(file_path, 'r', encoding=self.csv_encoding, newline='') as f:
                reader = csv.reader(f, delimiter=self.csv_delimiter)
                
                # Read header (first row)
                try:
                    header = next(reader)
                except StopIteration:
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
                
                # Normalize header columns
                normalized_header = [self._normalize_column_name(col) for col in header]
                
                logger.debug(f"Header columns: {header}")
                logger.debug(f"Normalized header: {normalized_header}")
                
                # Check for required columns
                all_columns_found = True
                for required_col in required_columns:
                    normalized_required = self._normalize_column_name(required_col)
                    
                    if normalized_required not in normalized_header:
                        error = ValidationError(
                            error_level='error',
                            error_text=f"Required column '{required_col}' is missing",
                            file_name=file_path.name,
                            folder_name=folder_name,
                            line_number=0
                        )
                        self.errors.append(error)
                        logger.error(
                            f"Missing column '{required_col}' in {file_path.name}"
                        )
                        all_columns_found = False
                
                if all_columns_found:
                    logger.info(f"All required columns found in: {file_path.name}")
                
                return all_columns_found
                
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
    
    def validate_folder(self, folder_name: str) -> bool:

        logger.info(f"Starting validation for folder: {folder_name}")
        
        # Step 1: Check if folder exists
        if not self.validate_folder_exists(folder_name):
            return False
        
        # Step 2: Check if folder has files
        if not self.validate_folder_has_files(folder_name):
            return False
        
        # Step 3: Validate columns in each CSV file
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
        required_cols = self.required_columns.get(folder_name, [])
        
        if not required_cols:
            logger.warning(
                f"No required columns configured for folder: {folder_name}"
            )
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
        logger.info("Starting validation for all folders")
       
        all_valid = True
        
        for folder_name in self.required_columns.keys():
            is_valid = self.validate_folder(folder_name)
            if not is_valid:
                all_valid = False
        
        logger.info("="*60)
        logger.info(f"Validation completed. Total errors: {len(self.errors)}")
        logger.info("="*60)
        
        return all_valid
    
    def generate_report(self, output_path: Optional[Path] = None) -> Path:

        if output_path is None:
            # Default: save to static folder with timestamp
            report_prefix = os.getenv('REPORT_PREFIX', 'validation_report')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{report_prefix}_{timestamp}.csv"
            
            static_folder = self.base_path / os.getenv('STATIC_FOLDER', 'static')
            static_folder.mkdir(parents=True, exist_ok=True)
            
            output_path = static_folder / report_filename
        
        logger.info(f"Generating validation report: {output_path}")
        
        # Write report
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = [
                'error_level',
                'error_text',
                'file_name',
                'folder_name',
                'line_number'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for error in self.errors:
                writer.writerow(error.to_dict())
        
        logger.info(f"Report generated successfully: {output_path}")
        logger.info(f"Total entries in report: {len(self.errors)}")
        
        return output_path
    
    def get_error_summary(self) -> Dict[str, int]:

        summary = {'error': 0, 'warning': 0, 'info': 0}
        
        for error in self.errors:
            level = error.error_level
            if level in summary:
                summary[level] += 1
        
        return summary