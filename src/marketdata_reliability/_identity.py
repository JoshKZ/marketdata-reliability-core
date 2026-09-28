"""Private v2 byte framing. Changes require a new identity version, not a rehash."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

OBSERVATION_PREFIX = "mdrc:observation:v2:"
LINEAGE_PREFIX = "mdrc:lineage:v2:"
_HEADER = b"mdrc-identity\x00v2\x00"


def text_bytes(value: str, field_name: str) -> bytes:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.encode("utf-8")


def fingerprint(kind: str, parts: Iterable[bytes]) -> str:
    """Hash a domain and counted, length-prefixed byte fields; never delimiters."""
    fields = (kind.encode("ascii"), *parts)
    digest = hashlib.sha256(_HEADER)
    digest.update(len(fields).to_bytes(8, "big"))
    for part in fields:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return f"mdrc:{kind}:v2:{digest.hexdigest()}"


def instrument_parts(market: str, symbol: str, asset_class: str) -> tuple[bytes, ...]:
    return (text_bytes(market, "market"), text_bytes(symbol, "symbol"),
            text_bytes(asset_class, "asset_class"))


def observation_fingerprint(
    provider: str, market: str, symbol: str, asset_class: str,
    event_time_utc: str, request_id: str, payload: bytes,
) -> str:
    if not isinstance(payload, bytes):
        raise TypeError("v2 observation payload must be immutable bytes")
    return fingerprint("observation", (
        text_bytes(provider, "provider"), *instrument_parts(market, symbol, asset_class),
        event_time_utc.encode("ascii"), text_bytes(request_id, "request_id"), payload,
    ))


def lineage_fingerprint(output_key: str, transformation: str, sources: tuple[str, ...]) -> str:
    return fingerprint("lineage", (
        text_bytes(output_key, "output_key"), text_bytes(transformation, "transformation"),
        *(text_bytes(source, "source_observation_id") for source in sources),
    ))
