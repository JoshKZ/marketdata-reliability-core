# Versioned identities and migration safety

Version 0.4.0 adds **opt-in v2 identity framing**. Existing `stable_key()`,
`build_observation()`, and `build_lineage()` retain their v1 outputs. Nothing
silently rehashes historical records, edits a database, or changes the CSV audit.
For new identity-sensitive integrations, use the v2 functions below.

## Why a new encoding

Issue #11 records a real ambiguity: `InstrumentId("A", "D", "B:C")` and
`InstrumentId("A:B", "D", "C")` both have the legacy string `A:B:C:D`. That string
is also an input to v1 observation hashing. Separately, the unit separator
`\x1f` can occur inside observation and lineage components, making different
component boundaries encode to the same v1 byte stream.

These are **framing ambiguities, not attacks on SHA-256**. Changing the hash
algorithm alone would not resolve them. V2 hashes explicit field lengths and a
versioned domain. Legacy identifiers remain supported for compatibility but
should not be used as unambiguous composite keys for unrestricted components.

## Public entry points

```python
from datetime import UTC, datetime
from marketdata_reliability import (
    InstrumentId, build_observation_v2, build_lineage_v2, instrument_key_v2,
)

instrument = InstrumentId("SYNTH", "DEMO", "equity")
now = datetime(2026, 1, 2, 9, tzinfo=UTC)
source = build_observation_v2(
    provider="synthetic", instrument=instrument, event_time=now, observed_at=now,
    request_id="request-1", payload={"close": "100"},
)
record = build_lineage_v2(
    output_key="synthetic-output", transformation="normalize:v1",
    source_observation_ids=[source.observation_id], created_at=now,
)
assert instrument_key_v2(instrument).startswith("mdrc:instrument:v2:")
assert source.observation_id.startswith("mdrc:observation:v2:")
assert record.lineage_id.startswith("mdrc:lineage:v2:")
```

The builders return existing `SourceObservation` and `LineageRecord` types;
their dataclass fields and old constructor signatures are unchanged. V2 records
validate that their declared ID matches their hashed fields on construction
(including `dataclasses.replace`). V2 payloads must be immutable `bytes` and v2
lineage sources are copied to a tuple. This is ordinary API validation, not a
sandbox against deliberate Python object mutation or an authenticity certificate.

### Exact byte specification

V2 IDs use `mdrc:<kind>:v2:<64 lowercase SHA-256 hex characters>`. The hash input is:

1. Header bytes `b"mdrc-identity\x00v2\x00"`.
2. Count of all fields, **including the domain field**, as unsigned 64-bit big-endian.
3. For each field: its unsigned 64-bit big-endian **byte length**, then exact bytes.

The first field is the ASCII kind: `instrument`, `observation`, or `lineage`.
Remaining fields, in order, are:

| Kind | Ordered fields after the domain |
| --- | --- |
| instrument | market, symbol, asset_class |
| observation | provider, market, symbol, asset_class, UTC event_time, request_id, stored payload bytes |
| lineage | output_key, transformation, each source observation ID in caller order |

Text fields are UTF-8; they must be nonblank. No stripping, case folding, or
Unicode normalization occurs. Canonically equivalent Unicode spellings remain
distinct byte inputs. Event time is UTC ISO 8601 with six fractional digits and
`+00:00`. Source order and source count matter. `observed_at` and `created_at`
remain audit metadata outside their respective fingerprints. Preserve the original
observation timestamp on replays: the reference store still compares whole records
and rejects same-ID evidence with different immutable metadata.

Hashes are not signatures, proofs of truth, or guarantees of zero cryptographic
collisions. A valid lineage ID does not verify that source IDs exist or that a
transformation was actually performed. Components and provenance must still be
validated by the caller.

### Payload semantics did not change

`build_observation_v2` deliberately uses the same stored-payload serialization as
`build_observation`. It hashes those stored bytes, **not original Python type
identity**. For example, Decimal values serialize to decimal strings and datetimes
to UTC strings; corresponding literal strings can have the same stored bytes.
Raw observations can preserve invalid market data for later validation. V2 does
not make the existing serializer type-preserving or certify a valid market price.
The migration planner never parses, reserializes, rounds, or normalizes payloads.

## Read-only migration planning

```python
from dataclasses import replace
from marketdata_reliability import plan_observation_migration

# legacy_records must contain complete original evidence, not just old ID strings.
plan = plan_observation_migration(legacy_records)
migrated = [replace(legacy_records[e.source_index], observation_id=e.new_id) for e in plan]
```

`plan_observation_migration(observations, *, max_records=100_000)` returns a tuple
of frozen `IdentityMigration(source_index, old_id, new_id)` entries. It checks old
v1 IDs against the exact evidence; verified v2 IDs map to themselves. Duplicate
input rows retain their indices: this helper does not deduplicate observations.
An empty batch yields an empty plan. Custom IDs, mismatched evidence, or one old ID
mapping to multiple v2 IDs raise `IdentityMigrationError`, with **no partial result**.
An invalid item type raises `TypeError`; an invalid positive-integer limit raises
`ValueError` before consuming input. An over-limit iterator may be read one item
beyond the configured limit to detect overflow. Results are batch-memory objects,
not a hard process-memory limit, durable receipt, or transactional write.

A collision check only covers the supplied batch. Separately successful batches
can still conflict globally. Reconcile mappings across the complete intended
migration scope before changing storage. Do not collapse the plan into an old-ID
dictionary before checking ambiguity. If v1 data was already overwritten, this
helper cannot reconstruct evidence that no longer exists.

### Storage upgrade sequence (owned by the integrator)

Back up original evidence and references first. Add storage capable of the full
namespaced strings (instrument IDs are 83 characters, observation IDs 84, and
lineage IDs 80); do not truncate them to a legacy 64-character column. Run the
planner on complete evidence and reconcile any ambiguities explicitly. Preserve
old/new mappings and all original bytes/timestamps; prepare referential updates
for bars, lineage source references, caches, and other consumers. Rebuild lineage
with `build_lineage_v2` from the explicitly selected source IDs; the library does
not guess how to retarget references. Apply the reviewed changes within the
storage system's transaction/rollback process, recheck old IDs and exact evidence
at application time, and verify referential integrity.

Legacy builders remain explicit compatibility tools, not the preferred path for
new unrestricted identities. There is no forced migration and no hidden warning
policy that rewrites user records. No database adapter, vendor material, or private
production schema is needed for this upgrade.

Run the fully synthetic example with:

```bash
python examples/migrate_identities.py
```

It verifies unchanged payloads, new lineage references, and refusal of an ambiguous
legacy mapping. It does not write files, access the network, or modify a database.
`tests/test_identity.py` pins legacy IDs, checks fixed v2 vectors and an independent
framing oracle, and covers delimiter/Unicode components and migration failure modes.
