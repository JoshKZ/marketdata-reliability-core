"""Demonstrate explicit, in-memory identity migration using synthetic evidence."""

from dataclasses import replace
from datetime import UTC, datetime

from marketdata_reliability import (
    IdentityMigrationError,
    InstrumentId,
    build_lineage_v2,
    build_observation,
    build_observation_v2,
    plan_observation_migration,
)


def main() -> None:
    now = datetime(2026, 1, 2, 9, tzinfo=UTC)
    kwargs = dict(provider="synthetic", instrument=InstrumentId("SYNTH", "DEMO", "equity"),
                  event_time=now, observed_at=now, request_id="request-1", payload={"close": "100"})
    legacy = build_observation(**kwargs)
    entry, = plan_observation_migration([legacy])
    migrated = replace(legacy, observation_id=entry.new_id)
    assert migrated == build_observation_v2(**kwargs)
    assert migrated.payload == legacy.payload and migrated.observed_at == legacy.observed_at
    assert migrated.observation_id != legacy.observation_id
    record = build_lineage_v2(output_key="synthetic-output", transformation="normalize:v1",
                              source_observation_ids=[migrated.observation_id], created_at=now)
    assert record.source_observation_ids == (migrated.observation_id,)
    print("Verified mapping; source payload bytes and audit timestamp preserved.")
    print("Explicit v2 lineage references the migrated observation.")
    ambiguous = [build_observation(**(kwargs | {"instrument": instrument})) for instrument in (
        InstrumentId("A", "D", "B:C"), InstrumentId("A:B", "D", "C"),
    )]
    try:
        plan_observation_migration(ambiguous)
    except IdentityMigrationError:
        print("Ambiguous legacy mapping rejected; no partial plan returned.")
    else:
        raise AssertionError("ambiguous mapping must not be accepted")
    print("No files or databases modified. Reconcile real storage and foreign keys separately.")


if __name__ == "__main__":
    main()
