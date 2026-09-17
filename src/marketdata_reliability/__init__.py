"""Public API for Market Data Reliability Core."""

from .correction import (
    CorrectionPreconditionFailed,
    CorrectionProposal,
    CorrectionReceipt,
    verify_correction,
)
from .ingestion import (
    InMemoryObservationStore,
    InsertDisposition,
    ObservationCollisionError,
)
from .models import Bar, InstrumentId, SourceObservation, build_observation
from .normalization import BarFieldMap, NormalizationError, normalize_bar
from .point_in_time import UniverseInterval, members_at
from .provenance import LineageRecord, build_lineage
from .validation import ValidationCode, ValidationIssue, validate_bar, validate_bars

__all__ = [
    "Bar",
    "BarFieldMap",
    "CorrectionPreconditionFailed",
    "CorrectionProposal",
    "CorrectionReceipt",
    "InMemoryObservationStore",
    "InsertDisposition",
    "InstrumentId",
    "LineageRecord",
    "NormalizationError",
    "ObservationCollisionError",
    "SourceObservation",
    "UniverseInterval",
    "ValidationCode",
    "ValidationIssue",
    "build_lineage",
    "build_observation",
    "members_at",
    "normalize_bar",
    "validate_bar",
    "validate_bars",
    "verify_correction",
]
