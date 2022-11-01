import logging
from logging.config import dictConfig
import importlib


def getlogger(
    log_level: int,
    handler: str = None,
    handler_config: dict = {},
    disable_existing_loggers: bool = False,
) -> logging.Logger:

    logger = dictConfig(
        {"version": 1, "disable_existing_loggers": disable_existing_loggers}
    )

    logger = logging.getLogger()

    logger.setLevel(log_level)
    if handler is not None:
        handler_str = handler
        handler_pkg = ".".join(handler_str.split(".")[:-1])
        handler_name = handler_str.split(".")[-1]
        handler_class = getattr(importlib.import_module(handler_pkg), handler_name)
        handler_instance = handler_class(**handler_config)
        logger.addHandler(handler_instance)
    return logger
