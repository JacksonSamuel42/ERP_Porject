import sys

from loguru import logger


def setup_app_logging():
    """Configura o Loguru para substituir logs padrão e prints."""

    logger.remove()

    logger.add(
        sys.stdout,
        colorize=True,
        format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        level='INFO',
    )

    logger.add(
        'logs/app_runtime.log',
        rotation='10 MB',
        retention='30 days',
        compression='zip',
        level='WARNING',
        format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}',
    )

    return logger
