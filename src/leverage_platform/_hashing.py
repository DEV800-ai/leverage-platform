"""SHA-256 hashing utilities for prompt/input/output audit (see ADR-003)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_template(template: str) -> str:
    """Hash a prompt template (UTF-8 bytes, before variable substitution).

    Returns 64-char hex SHA-256 string.
    """
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


def hash_inputs(variables: dict[str, Any]) -> str:
    """Hash variables passed into a prompt template.

    Uses canonical JSON: sorted keys, no whitespace, UTF-8.
    Returns 64-char hex SHA-256 string.
    """
    canonical = json.dumps(variables, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_output(payload: dict[str, Any]) -> str:
    """Hash a validated output JSON payload.

    Same canonicalization rules as `hash_inputs`. Returns 64-char hex.
    """
    return hash_inputs(payload)


def _json_default(obj: Any) -> Any:
    """Fallback serializer for non-JSON-native types."""
    # Decimal, UUID, datetime — fall back to str()
    return str(obj)
