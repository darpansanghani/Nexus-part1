"""Structured logging configuration for NEXUS."""

import json
import logging
import sys
from typing import Any, Mapping


class JsonFormatter(logging.Formatter):
    """Custom formatter to output JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.
        
        Args:
            record: The log record to format.
            
        Returns:
            The formatted JSON string.
        """
        log_entry: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, self.datefmt),
            "file": record.filename,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Retrieve a configured JSON logger.
    
    Args:
        name: The name of the logger (typically __name__).
        
    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers if get_logger is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    # Do not propagate to root logger which might format differently
    logger.propagate = False
    
    return logger
