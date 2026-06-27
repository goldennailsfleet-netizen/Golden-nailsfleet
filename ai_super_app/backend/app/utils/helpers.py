"""
Helper Functions
"""
import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict


def generate_cache_key(data: Dict[str, Any]) -> str:
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


def format_timestamp(dt: datetime) -> str:
    return dt.isoformat()


def truncate_text(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
