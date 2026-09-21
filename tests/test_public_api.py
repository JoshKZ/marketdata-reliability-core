V0_1_PUBLIC_API = {
    "Bar", "BarFieldMap", "CorrectionPreconditionFailed", "CorrectionProposal",
    "CorrectionReceipt", "InMemoryObservationStore", "InsertDisposition", "InstrumentId",
    "LineageRecord", "NormalizationError", "ObservationCollisionError", "SourceObservation",
    "UniverseInterval", "ValidationCode", "ValidationIssue", "build_lineage", "build_observation",
    "members_at", "normalize_bar", "validate_bar", "validate_bars", "verify_correction",
}
V0_2_ADDITIONS = {
    "InstrumentReport", "ValidationReport", "ValidationSeverity", "ValidationWindow",
    "WindowReport", "audit_bars",
}


def test_package_root_exports_frozen_v0_1_api() -> None:
    import marketdata_reliability as mdr

    assert V0_1_PUBLIC_API <= set(mdr.__all__)
    for name in V0_1_PUBLIC_API:
        assert getattr(mdr, name) is not None


def test_package_root_exports_exact_v0_2_api() -> None:
    import marketdata_reliability as mdr

    assert len(mdr.__all__) == len(set(mdr.__all__))
    assert set(mdr.__all__) == V0_1_PUBLIC_API | V0_2_ADDITIONS
    for name in V0_2_ADDITIONS:
        assert getattr(mdr, name) is not None
