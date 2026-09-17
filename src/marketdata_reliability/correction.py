"""Precondition checks for safe historical corrections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class CorrectionPreconditionFailed(ValueError):
    """Raised when current data no longer matches a correction proposal."""


@dataclass(frozen=True, slots=True)
class CorrectionProposal:
    record_key: str
    field: str
    expected_value: Any
    replacement_value: Any
    evidence_ref: str
    reason: str

    def __post_init__(self) -> None:
        for name, value in (
            ("record_key", self.record_key),
            ("field", self.field),
            ("evidence_ref", self.evidence_ref),
            ("reason", self.reason),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class CorrectionReceipt:
    record_key: str
    field: str
    observed_value: Any
    expected_value: Any
    replacement_value: Any
    evidence_ref: str
    checked_at: datetime
    authorized: bool = True


def verify_correction(
    proposal: CorrectionProposal,
    observed_value: Any,
    *,
    checked_at: datetime | None = None,
) -> CorrectionReceipt:
    """Authorize a correction only if the current value still matches expectation.

    This function intentionally performs no persistence. Database adapters should call it
    immediately before their own compare-and-set or equivalent write operation.
    """

    if observed_value != proposal.expected_value:
        raise CorrectionPreconditionFailed(
            "observed value does not match correction proposal's expected value"
        )

    instant = checked_at or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("checked_at must be timezone-aware")

    return CorrectionReceipt(
        record_key=proposal.record_key,
        field=proposal.field,
        observed_value=observed_value,
        expected_value=proposal.expected_value,
        replacement_value=proposal.replacement_value,
        evidence_ref=proposal.evidence_ref,
        checked_at=instant,
    )
