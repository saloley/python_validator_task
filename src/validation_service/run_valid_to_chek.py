import os
import json
from pathlib import Path
from dotenv import load_dotenv
from .validator import FileValidator
from .logger_config import logger


load_dotenv()


def load_required_columns_config(config_path: Path) -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info(f"Configuration loaded from: {config_path}")
        logger.debug(f"Configuration content: {config}")

        return config

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise

    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


def main():
    logger.info("step1")

    try:
        # Get configuration from environment
        base_path = os.getenv('BASE_PATH', '')
        csv_delimiter = os.getenv('CSV_DELIMITER', ',')
        csv_encoding = os.getenv('CSV_ENCODING', '')

        # Resolve base path relative to project root
        # Assuming this script is in src/validation_service/
        project_root = Path(__file__).parent.parent.parent
        full_base_path = project_root / base_path

        logger.info(f"Project root: {project_root}")
        logger.info(f"Base path: {full_base_path}")
        logger.info(f"CSV delimiter: '{csv_delimiter}'")
        logger.info(f"CSV encoding: {csv_encoding}")

        # Load required columns configuration
        config_file = Path(__file__).parent / 'config.json'
        required_columns_config = load_required_columns_config(config_file)

        # Create validator
        validator = FileValidator(
            base_path=str(full_base_path),
            required_columns_config=required_columns_config,
            csv_delimiter=csv_delimiter,
            csv_encoding=csv_encoding
        )

        # Run validation
        logger.info("STARTING VALIDATION PROCESS")


        validation_passed = validator.validate_all_folders()

        # Generate report
        logger.info("GENERATING VALIDATION REPORT")

        report_path = validator.generate_report()

        # Print summary
        logger.info("VALIDATION SUMMARY")

        summary = validator.get_error_summary()
        logger.info(f"Errors:   {summary['error']}")
        logger.info(f"Warnings: {summary['warning']}")
        logger.info(f"Info:     {summary['info']}")
        logger.info(f"Total:    {sum(summary.values())}")

        logger.info(f"Report saved to: {report_path}")

        # Exit status
        if validation_passed and summary['error'] == 0:
            logger.info("\n VALIDATION PASSED")
            return 0
        else:
            logger.warning("\n VALIDATION FAILED")
            return 1

    except Exception as e:
        logger.error(f"\n VALIDATION ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)