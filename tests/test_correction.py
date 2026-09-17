from datetime import datetime, timezone

import pytest

from marketdata_reliability import (
    CorrectionPreconditionFailed,
    CorrectionProposal,
    verify_correction,
)


def test_correction_requires_expected_value_to_still_match() -> None:
    proposal = CorrectionProposal(
        record_key="DEMO:2026-01-02",
        field="close",
        expected_value="100.00",
        replacement_value="100.25",
        evidence_ref="public-source:example-1",
        reason="source reconciliation",
    )

    receipt = verify_correction(
        proposal,
        "100.00",
        checked_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )
    assert receipt.authorized is True
    assert receipt.replacement_value == "100.25"

    with pytest.raises(CorrectionPreconditionFailed):
        verify_correction(proposal, "99.50")
