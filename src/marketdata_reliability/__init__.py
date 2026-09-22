"""Public API for Market Data Reliability Core."""

from .audit import InstrumentReport, ValidationReport, ValidationWindow, WindowReport, audit_bars
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
from .reporting import report_to_dict, report_to_json
from .validation import (
    ValidationCode,
    ValidationIssue,
    ValidationSeverity,
    validate_bar,
    validate_bars,
)

__all__ = [
    "Bar",
    "BarFieldMap",
    "CorrectionPreconditionFailed",
    "CorrectionProposal",
    "CorrectionReceipt",
    "InMemoryObservationStore",
    "InsertDisposition",
    "InstrumentId",
    "InstrumentReport",
    "LineageRecord",
    "NormalizationError",
    "ObservationCollisionError",
    "SourceObservation",
    "UniverseInterval",
    "ValidationCode",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
    "ValidationWindow",
    "WindowReport",
    "audit_bars",
    "build_lineage",
    "build_observation",
    "members_at",
    "normalize_bar",
    "report_to_dict",
    "report_to_json",
    "validate_bar",
    "validate_bars",
    "verify_correction",
]
