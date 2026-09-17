from datetime import datetime, timedelta, timezone

import pytest

from marketdata_reliability import build_lineage

UTC = timezone.utc


def test_lineage_identity_is_deterministic_and_ignores_creation_time() -> None:
    first = build_lineage(
        output_key="XNAS:equity:DEMO:2026-01-02T14:30Z:1m",
        transformation="normalize_ohlcv:v1",
        source_observation_ids=["obs-1", "obs-2"],
        created_at=datetime(2026, 1, 2, 14, 32, tzinfo=UTC),
    )
    second = build_lineage(
        output_key=first.output_key,
        transformation=first.transformation,
        source_observation_ids=first.source_observation_ids,
        created_at=first.created_at + timedelta(minutes=5),
    )

    assert first.lineage_id == second.lineage_id


def test_source_order_is_part_of_lineage_identity() -> None:
    first = build_lineage(
        output_key="bar-1",
        transformation="aggregate:v1",
        source_observation_ids=["obs-1", "obs-2"],
        created_at=datetime(2026, 1, 2, 14, 32, tzinfo=UTC),
    )
    reversed_sources = build_lineage(
        output_key="bar-1",
        transformation="aggregate:v1",
        source_observation_ids=["obs-2", "obs-1"],
        created_at=first.created_at,
    )

    assert first.lineage_id != reversed_sources.lineage_id


def test_lineage_rejects_duplicate_sources_and_naive_time() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        build_lineage(
            output_key="bar-1",
            transformation="aggregate:v1",
            source_observation_ids=["obs-1", "obs-1"],
            created_at=datetime(2026, 1, 2, 14, 32, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        build_lineage(
            output_key="bar-1",
            transformation="aggregate:v1",
            source_observation_ids=["obs-1"],
            created_at=datetime(2026, 1, 2, 14, 32),
        )
