"""
Base Validator with common validation methods
"""
import os
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

from .validation_error import ValidationError
from .logger_config import logger

load_dotenv()


class BaseValidator:
    def __init__(
        self,
        base_path: str,
        required_columns_config: Dict,
        csv_delimiter: str = ',',
        csv_encoding: str = 'utf-8'
    ):
        self.base_path = Path(base_path)
        self.required_columns = required_columns_config
        self.csv_delimiter = csv_delimiter
        self.csv_encoding = csv_encoding
        self.errors: List[ValidationError] = []
        
        logger.info(f"BaseValidator initialized with base_path: {self.base_path}")
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
                
                normalized_header = [self._normalize_column_name(col) for col in header]
                
                logger.debug(f"Header columns: {header}")
                logger.debug(f"Normalized header: {normalized_header}")
                
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
                        logger.error(f"Missing column '{required_col}' in {file_path.name}")
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
    
    def generate_report(self, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            report_prefix = os.getenv('REPORT_PREFIX', 'validation_report')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{report_prefix}_{timestamp}.csv"
            
            report_folder = os.getenv('REPORT_FOLDER', 'raw/reports')
            reports_folder = self.base_path / report_folder
            reports_folder.mkdir(parents=True, exist_ok=True)
    
            output_path = reports_folder / report_filename
        
        logger.info(f"Generating validation report: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = [
                'error_level',
                'error_text',
                'file_name',
                'folder_name',
                'line_number',
                'value_type',
                'value',
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
