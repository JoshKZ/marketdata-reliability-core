EXPECTED_PUBLIC_API = {
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
}


def test_package_root_exports_frozen_v0_1_api() -> None:
    import marketdata_reliability as mdr

    assert set(mdr.__all__) == EXPECTED_PUBLIC_API
    for name in EXPECTED_PUBLIC_API:
        assert getattr(mdr, name) is not None
