import logging
from logging.handlers import RotatingFileHandler
from . import config


def setup_logging(verbose: bool = False):
    """
    Configures the root logger to write ONLY to a file.
    No StreamHandler is added, so no logs appear in the CLI.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates if called multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Determine level based on verbose flag
    # If verbose: Log everything (DEBUG) to file
    # If normal: Log only events (INFO) to file
    log_level = logging.DEBUG if verbose else logging.INFO
    root_logger.setLevel(log_level)

    # Ensure config dir exists for the log file
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Create the file handler
    # 5MB per file, keep last 3 backups
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_format)

    root_logger.addHandler(file_handler)