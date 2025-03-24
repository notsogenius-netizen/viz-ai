import logging
from logging.config import dictConfig

class LoggingConfig:
    """
    Configures logging for the FastAPI application.
    """
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "[%(asctime)s] %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "app.log",
                "formatter": "detailed",
                "level": "INFO",
            }
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "app": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            }
        }
    }

    @staticmethod
    def apply():
        dictConfig(LoggingConfig.LOGGING_CONFIG)