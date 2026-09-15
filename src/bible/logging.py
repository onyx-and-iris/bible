import sys

from loguru import logger

VALID_LEVELS = {'TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'}


def configure_logging(level: str):
    if level.upper() not in VALID_LEVELS:
        raise ValueError(
            f'Invalid log level: {level}. Valid levels are: {", ".join(VALID_LEVELS)}'
        )

    logger.remove()
    logger.add(sys.stderr, level=level.upper())
