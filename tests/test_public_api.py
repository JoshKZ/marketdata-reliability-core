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
V0_3_ADDITIONS = {"report_to_dict", "report_to_json"}


def test_package_root_preserves_all_previous_exports() -> None:
    import marketdata_reliability as mdr

    previous = V0_1_PUBLIC_API | V0_2_ADDITIONS
    assert previous <= set(mdr.__all__)
    for name in previous:
        assert getattr(mdr, name) is not None


def test_package_root_exports_exact_v0_3_api() -> None:
    import marketdata_reliability as mdr

    assert len(mdr.__all__) == len(set(mdr.__all__))
    assert set(mdr.__all__) == V0_1_PUBLIC_API | V0_2_ADDITIONS | V0_3_ADDITIONS
    for name in V0_3_ADDITIONS:
        assert callable(getattr(mdr, name))
