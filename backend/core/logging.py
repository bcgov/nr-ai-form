"""
Centralized logging configuration using structlog.

This module provides a consistent logging setup across the entire application.
"""

import logging
import sys
from typing import Any, Optional

import structlog

from backend.core.config import settings


def configure_structlog(
    log_level: str = "INFO",
) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json_format: Whether to use JSON formatting for logs
        include_timestamp: Whether to include timestamps in logs
    """
    # Set up processors based on configuration
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: Optional[float] = None,
    user_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Helper function to log API requests in a consistent format.

    Args:
        logger: Structlog logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        user_id: User identifier (if available)
        **kwargs: Additional context to include in the log
    """
    log_data = {
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
    }

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if user_id is not None:
        log_data["user_id"] = user_id

    # Add any additional context
    log_data.update(kwargs)

    # Log at appropriate level based on status code
    if status_code >= 500:
        logger.error("API request completed", **log_data)
    elif status_code >= 400:
        logger.warning("API request completed", **log_data)
    else:
        logger.info("API request completed", **log_data)


def log_azure_operation(
    logger: structlog.BoundLogger,
    operation: str,
    service: str,
    success: bool,
    duration_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """
    Helper function to log Azure service operations in a consistent format.

    Args:
        logger: Structlog logger instance
        operation: Operation name (e.g., 'search', 'blob_upload', 'openai_chat')
        service: Azure service name (e.g., 'search', 'storage', 'openai')
        success: Whether the operation was successful
        duration_ms: Operation duration in milliseconds
        error_message: Error message if operation failed
        **kwargs: Additional context to include in the log
    """
    log_data = {
        "event": "azure_operation",
        "operation": operation,
        "service": service,
        "success": success,
    }

    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms

    if error_message is not None:
        log_data["error_message"] = error_message

    # Add any additional context
    log_data.update(kwargs)

    # Log at appropriate level based on success
    if success:
        logger.info("Azure operation completed", **log_data)
    else:
        logger.error("Azure operation failed", **log_data)


# Initialize logging when module is imported
configure_structlog(
    log_level="DEBUG" if settings.DEBUG else "INFO",
)
