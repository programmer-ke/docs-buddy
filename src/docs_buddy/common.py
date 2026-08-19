"""Custom functionality to be re-used across all packages

Should not have any local imports
"""

import datetime
import os
from typing import TypeAlias
import logging
import functools
import re

PathLike: TypeAlias = str | os.PathLike


class DocsBuddyError(Exception):
    pass


def json_datetime_handler(obj):
    """Serializes date and time objects to string

    Used as a default handler by json.dump
    """

    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, datetime.time):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not JSON serializable")


def log_input(logger, log_level):
    """Creates a decorator that logs function input at the given log level"""

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = "%s called with args: %s and kwargs: %s"
            logger.log(log_level, msg, func.__name__, args, kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_to_python_id(identifier: str) -> str:
    """Converts string to valid Python identifier"""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", identifier)
    if sanitized[0].isdigit():
        sanitized = "name_" + sanitized
    return sanitized
