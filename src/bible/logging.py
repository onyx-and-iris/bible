import sys
from enum import IntEnum

from loguru import logger


class LogOutputType(IntEnum):
    CONSOLE = 1
    FILE = 2
    BOTH = 3


VALID_LEVELS = {
    'TRACE',
    'DEBUG',
    'INFO',
    'SUCCESS',
    'WARNING',
    'ERROR',
    'CRITICAL',
}


def configure_logging(
    level: str,
    output_type: list[LogOutputType] = [LogOutputType.CONSOLE],
    log_path: str = 'app.log',
):
    if level.upper() not in VALID_LEVELS:
        raise ValueError(
            f'Invalid log level: {level}. Valid levels are: {", ".join(VALID_LEVELS)}'
        )

    logger.remove()
    if LogOutputType.CONSOLE in output_type or LogOutputType.BOTH in output_type:
        logger.add(sys.stderr, level=level.upper())
    if LogOutputType.FILE in output_type or LogOutputType.BOTH in output_type:
        logger.add(log_path, level=level.upper())
