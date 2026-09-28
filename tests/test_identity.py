"""Regression contracts for versioned identity and non-mutating migration."""

import hashlib
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from itertools import product

import pytest

from marketdata_reliability import (
    IdentityMigrationError,
    InMemoryObservationStore,
    InsertDisposition,
    InstrumentId,
    LineageRecord,
    ObservationCollisionError,
    SourceObservation,
    build_lineage,
    build_lineage_v2,
    build_observation,
    build_observation_v2,
    instrument_key_v2,
    plan_observation_migration,
)

NOW = datetime(2026, 1, 2, 9, tzinfo=UTC)
INSTRUMENT = InstrumentId("SYNTH", "DEMO", "equity")


def observation(builder=build_observation, **changes):
    kwargs = dict(provider="synthetic", instrument=INSTRUMENT, event_time=NOW,
                  observed_at=NOW, request_id="request-1", payload={"close": "100"})
    kwargs.update(changes)
    return builder(**kwargs)


def lineage(builder=build_lineage, **changes):
    kwargs = dict(output_key="out", transformation="normalize:v1",
                  source_observation_ids=["s1", "s2"], created_at=NOW)
    kwargs.update(changes)
    return builder(**kwargs)


def reference_id(kind, parts):
    """Independent specification oracle: count, then unsigned 64-bit byte lengths."""
    fields = [kind.encode("ascii"), *parts]
    data = b"mdrc-identity\x00v2\x00" + len(fields).to_bytes(8, "big")
    data += b"".join(len(part).to_bytes(8, "big") + part for part in fields)
    return f"mdrc:{kind}:v2:" + hashlib.sha256(data).hexdigest()


def test_legacy_ids_and_constructor_shape_remain_unchanged():
    from dataclasses import fields

    assert INSTRUMENT.stable_key() == "SYNTH:equity:DEMO"
    assert observation().observation_id == "80f40acd8e9483238302192d00a6bcf811965d492eeff05f9f2e2da797fc0cfa"
    assert lineage().lineage_id == "07f0fd1b694c509f738eab3c605c3b5d7c9e45ca445f4c8ca23c9c947d4302e9"
    assert [f.name for f in fields(SourceObservation)] == [
        "observation_id", "provider", "instrument", "event_time", "observed_at", "request_id", "payload",
    ]
    assert [f.name for f in fields(LineageRecord)] == [
        "lineage_id", "output_key", "transformation", "source_observation_ids", "created_at",
    ]


def test_colon_ambiguity_is_reproduced_and_v2_separates_it():
    first, second = InstrumentId("A", "D", "B:C"), InstrumentId("A:B", "D", "C")
    assert first != second and first.stable_key() == second.stable_key()
    assert observation(instrument=first).observation_id == observation(instrument=second).observation_id
    assert instrument_key_v2(first) != instrument_key_v2(second)
    assert observation(build_observation_v2, instrument=first).observation_id != observation(
        build_observation_v2, instrument=second).observation_id


def test_observation_separator_ambiguity_is_reproduced_and_v2_separates_it():
    first = dict(provider="p\x1fA", instrument=InstrumentId("B", "D", "C"))
    second = dict(provider="p", instrument=InstrumentId("A\x1fB", "D", "C"))
    assert observation(**first).observation_id == observation(**second).observation_id
    assert observation(build_observation_v2, **first).observation_id != observation(
        build_observation_v2, **second).observation_id


@pytest.mark.parametrize("first,second", [
    (dict(output_key="a\x1fb", transformation="c"), dict(output_key="a", transformation="b\x1fc")),
    (dict(source_observation_ids=["a\x1fb"]), dict(source_observation_ids=["a", "b"])),
    (dict(source_observation_ids=["a\x1fb", "c"]), dict(source_observation_ids=["a", "b\x1fc"])),
])
def test_lineage_separator_ambiguities_are_reproduced_and_v2_separates_them(first, second):
    assert lineage(**first).lineage_id == lineage(**second).lineage_id
    assert lineage(build_lineage_v2, **first).lineage_id != lineage(build_lineage_v2, **second).lineage_id


def test_v2_hashes_match_independent_specification():
    key = instrument_key_v2(INSTRUMENT)
    assert key == reference_id("instrument", [b"SYNTH", b"DEMO", b"equity"])
    source = observation(build_observation_v2)
    assert source.observation_id == reference_id("observation", [
        b"synthetic", b"SYNTH", b"DEMO", b"equity", b"2026-01-02T09:00:00.000000+00:00",
        b"request-1", b'{"close":"100"}',
    ])
    record = lineage(build_lineage_v2)
    assert record.lineage_id == reference_id("lineage", [b"out", b"normalize:v1", b"s1", b"s2"])
    assert len({key, source.observation_id, record.lineage_id}) == 3


def test_exhaustive_component_framing_and_unicode_byte_lengths():
    components = ["x", "a:b", "a\x1fb", "\x00x", "測試", "é", "e\u0301", '"\\x']
    keys = set()
    for market, symbol, asset in product(components, repeat=3):
        instrument = InstrumentId(market, symbol, asset)
        key = instrument_key_v2(instrument)
        assert key == reference_id("instrument", [p.encode("utf-8") for p in (market, symbol, asset)])
        assert key not in keys
        keys.add(key)
    assert len(keys) == 512


@pytest.mark.parametrize("changes", [
    {"provider": "different"}, {"instrument": InstrumentId("SYNTH", "OTHER", "equity")},
    {"event_time": NOW + timedelta(microseconds=1)}, {"request_id": "different"},
    {"payload": {"close": "101"}},
])
def test_v2_observation_id_tracks_evidence_fields(changes):
    assert observation(build_observation_v2).observation_id != observation(build_observation_v2, **changes).observation_id


def test_observation_metadata_policy_and_timezone_equivalence():
    first = observation(build_observation_v2)
    same = observation(build_observation_v2, event_time=NOW.astimezone(timezone(timedelta(hours=8))))
    later = replace(first, observed_at=NOW + timedelta(days=1))
    assert first.observation_id == same.observation_id == later.observation_id
    store = InMemoryObservationStore()
    assert store.insert(first) is InsertDisposition.INSERTED
    assert store.insert(same) is InsertDisposition.DUPLICATE
    with pytest.raises(ObservationCollisionError):
        store.insert(later)  # Metadata still belongs to immutable evidence in the store.


def test_payload_serialization_is_unchanged_and_mapping_order_is_stable():
    from decimal import Decimal

    old = observation(payload={"a": Decimal("100.0"), "b": NOW})
    new = observation(build_observation_v2, payload={"b": NOW, "a": Decimal("100.0")})
    assert new.payload == old.payload
    equivalent = observation(build_observation_v2, payload={"a": "100.0", "b": "2026-01-02T09:00:00.000000+00:00"})
    assert new.observation_id == equivalent.observation_id  # Identity is over stored bytes, not Python types.


def test_lineage_order_matters_but_creation_time_does_not():
    base = lineage(build_lineage_v2)
    assert base.lineage_id != lineage(build_lineage_v2, source_observation_ids=["s2", "s1"]).lineage_id
    assert base.lineage_id == lineage(build_lineage_v2, created_at=NOW + timedelta(days=1)).lineage_id


def test_v2_lineage_snapshots_caller_sources():
    sources = ["s1", "s2"]
    record = lineage(build_lineage_v2, source_observation_ids=iter(sources))
    copied = replace(record, source_observation_ids=sources)
    sources.clear()
    assert record.source_observation_ids == copied.source_observation_ids == ("s1", "s2")
    with pytest.raises(FrozenInstanceError):
        record.output_key = "changed"


@pytest.mark.parametrize("changes", [
    {"provider": "changed"}, {"instrument": InstrumentId("X", "D")},
    {"event_time": NOW + timedelta(seconds=1)}, {"request_id": "changed"}, {"payload": b"changed"},
    {"observation_id": "mdrc:observation:v2:" + "0" * 64},
])
def test_v2_observation_direct_construction_cannot_claim_a_mismatched_id(changes):
    with pytest.raises(ValueError):
        replace(observation(build_observation_v2), **changes)


@pytest.mark.parametrize("changes", [
    {"output_key": "changed"}, {"transformation": "changed"}, {"source_observation_ids": ("other",)},
    {"lineage_id": "mdrc:lineage:v2:" + "0" * 64},
])
def test_v2_lineage_direct_construction_cannot_claim_a_mismatched_id(changes):
    with pytest.raises(ValueError):
        replace(lineage(build_lineage_v2), **changes)


@pytest.mark.parametrize("payload", [bytearray(b"abc"), memoryview(b"abc"), "abc"])
def test_v2_observation_rejects_mutable_or_non_bytes_payload(payload):
    with pytest.raises(TypeError):
        replace(observation(build_observation_v2), payload=payload)


@pytest.mark.parametrize("changes", [
    {"provider": ""}, {"request_id": " "}, {"event_time": NOW.replace(tzinfo=None)},
    {"observed_at": NOW.replace(tzinfo=None)},
])
def test_v2_observation_preserves_required_metadata_checks(changes):
    with pytest.raises(ValueError):
        observation(build_observation_v2, **changes)


@pytest.mark.parametrize("changes", [
    {"output_key": " "}, {"transformation": ""}, {"source_observation_ids": []},
    {"source_observation_ids": ["s", "s"]}, {"source_observation_ids": [""]},
    {"created_at": NOW.replace(tzinfo=None)},
])
def test_v2_lineage_rejects_invalid_parts(changes):
    with pytest.raises(ValueError):
        lineage(build_lineage_v2, **changes)


def test_migration_is_pure_preserves_rows_and_is_idempotent_for_v2():
    old = observation()
    new = observation(build_observation_v2)
    rows = [old, old, new]
    plan = plan_observation_migration(iter(rows))
    assert [(e.source_index, e.old_id, e.new_id) for e in plan] == [
        (0, old.observation_id, new.observation_id), (1, old.observation_id, new.observation_id),
        (2, new.observation_id, new.observation_id),
    ]
    assert rows == [old, old, new]
    assert old.payload == new.payload and old.observed_at == new.observed_at
    assert len(plan_observation_migration([])) == 0
    with pytest.raises(FrozenInstanceError):
        plan[0].old_id = "changed"


def test_migration_rejects_ambiguous_legacy_ids_instead_of_losing_a_row():
    records = [observation(instrument=i) for i in (InstrumentId("A", "D", "B:C"), InstrumentId("A:B", "D", "C"))]
    with pytest.raises(IdentityMigrationError, match="ambiguous"):
        plan_observation_migration(records)
    assert records[0].observation_id == records[1].observation_id


@pytest.mark.parametrize("changes", [{"observation_id": "custom-id"}, {"payload": b"changed"}])
def test_migration_rejects_unverifiable_legacy_records(changes):
    with pytest.raises(IdentityMigrationError):
        plan_observation_migration([replace(observation(), **changes)])


def test_migration_preserves_exact_payload_bytes_without_decoding():
    old = observation()
    raw = b"\x00\xff\x1fnot-json"
    parts = [old.provider, old.instrument.stable_key(), old.event_time.isoformat(timespec="microseconds"), old.request_id]
    legacy_id = hashlib.sha256(b"\x1f".join(p.encode() for p in parts) + b"\x1f" + raw).hexdigest()
    raw_record = replace(old, observation_id=legacy_id, payload=raw)
    entry, = plan_observation_migration([raw_record])
    migrated = replace(raw_record, observation_id=entry.new_id)
    assert migrated.payload == raw


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "10"])
def test_bad_migration_limit_fails_before_consuming_records(limit):
    def untouched():
        raise AssertionError("must not consume input")
        yield
    with pytest.raises(ValueError):
        plan_observation_migration(untouched(), max_records=limit)


def test_migration_resource_limit_and_invalid_record_type():
    assert len(plan_observation_migration([observation()], max_records=1)) == 1
    with pytest.raises(IdentityMigrationError, match="max_records"):
        plan_observation_migration([observation(), observation()], max_records=1)
    with pytest.raises(TypeError):
        plan_observation_migration([None])


def test_v2_published_golden_vectors():
    assert instrument_key_v2(INSTRUMENT) == 'mdrc:instrument:v2:908088551596b2e95fd50a2ab2a4adca23b14eb364eea16df192f4ac0276918e'
    assert observation(build_observation_v2).observation_id == 'mdrc:observation:v2:a7ccd054079cf209862066825803d17a0080e4cf9d24bff9cb5e2914824f7191'
    assert lineage(build_lineage_v2).lineage_id == 'mdrc:lineage:v2:d8a03a60a33c70ea3e9c6de9e96f963c348c451a3a8aa2bf577ada6497346491'
