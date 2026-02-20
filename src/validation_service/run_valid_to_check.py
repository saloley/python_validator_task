import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

from .raw_validator import RawValidator
from .logger_config import logger

load_dotenv()


CONFIG_FILE = Path(__file__).parent / 'config.json'

VALID_TYPES = ['raw', 'source', 'static']


def load_config(config_path: Path) -> dict:

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    logger.info(f"Configuration loaded from: {config_path}")
    return config


def get_validation_type() -> str:
    if len(sys.argv) > 1:
        validation_type = sys.argv[1].lower()
        if validation_type not in VALID_TYPES:
            logger.warning(
                f"Unknown validation type '{validation_type}', using 'raw' as default"
            )
            return 'raw'
        return validation_type
    return 'raw'


def main() -> int:

    logger.info("Starting validation service")


    validation_type = get_validation_type()
    logger.info(f"Validation type: {validation_type.upper()}")


    base_path = Path(os.getenv('BASE_PATH', 'src/files'))
    csv_delimiter = os.getenv('CSV_DELIMITER', ',')
    csv_encoding = os.getenv('CSV_ENCODING', 'utf-8')

    logger.info(f"Base path: {base_path}")
    logger.info(f"CSV delimiter: '{csv_delimiter}'")
    logger.info(f"CSV encoding: {csv_encoding}")


    try:
        config = load_config(CONFIG_FILE)
    except FileNotFoundError:
        logger.error(f"Config file not found: {CONFIG_FILE}")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        return 1

    # Create validator based on type
    if validation_type == 'raw':

        validator = RawValidator(
            base_path=str(base_path),
            required_columns_config=config,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding
        )

    # Run validation
    logger.info("STARTING VALIDATION PROCESS")
    validation_passed = validator.validate_all_folders()

    # Generate report
    logger.info("GENERATING VALIDATION REPORT")
    report_path = validator.generate_report()

    # Summary
    summary = validator.get_error_summary()
    logger.info("VALIDATION SUMMARY")
    logger.info(f"Errors:   {summary['error']}")
    logger.info(f"Warnings: {summary['warning']}")
    logger.info(f"Info:     {summary['info']}")
    logger.info(f"Total:    {sum(summary.values())}")
    logger.info(f"Report saved to: {report_path}")

    if validation_passed and summary['error'] == 0:
        logger.info("VALIDATION PASSED")
        return 0
    else:
        logger.warning("VALIDATION FAILED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)