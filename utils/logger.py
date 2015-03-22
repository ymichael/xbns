import config
import logging
import logging.handlers
import sys


def get_logger(name="Default"):
    logger = logging.getLogger(name)
    # TODO: Refactor debug level as a cli argument.
    logger.setLevel(logging.DEBUG)
    if len(logger.handlers) == 0:
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(asctime)s: %(message)s")
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        if config.SHOULD_LOG:
            file_handler = logging.handlers.RotatingFileHandler(
                config.LOG_FILE_NAME, backupCount=20, maxBytes=5242880)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    return logger