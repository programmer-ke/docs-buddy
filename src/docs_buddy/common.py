"""Custom functionality to be re-used across all packages

Should not have any local imports
"""

import datetime
import os

PathLike = str | os.PathLike


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
