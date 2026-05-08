"""
Shared JSON utilities for handling non-serializable DB types.
MySQL DECIMAL → float, date/datetime → ISO string.
"""

import json
from decimal import Decimal
from datetime import date, datetime


class DBEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


def sanitize(obj):
    """Recursively convert DB-unfriendly types in dicts/lists."""
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, cls=DBEncoder)
