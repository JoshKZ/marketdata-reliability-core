# OSS Extraction Boundary

This repository is a clean public implementation of generic market-data reliability ideas. It is not a source mirror of any private trading or production system.

## Safe to publish

Public contributions may include:

- provider-independent data models and interfaces;
- generic normalization and validation rules;
- immutable-observation and provenance primitives;
- idempotency, retry, checkpoint, receipt, and replay semantics;
- point-in-time membership and survivorship-bias protections;
- generic historical-correction preconditions and audit concepts;
- synthetic fixtures and public-data examples;
- tests, documentation, and benchmarks built from synthetic or appropriately licensed public data.

## Rewrite before publishing

A useful concept may exist inside a private or production system without its implementation being appropriate for this repository. Provider adapters, persistence logic, recovery code, market calendars, deployment glue, and operational tooling should be reimplemented against the public contracts when they contain environment-specific assumptions.

Do not bulk-copy private source trees or preserve private Git history here. Public implementation should be independently reviewable and free of hidden production dependencies.

## Never publish here

Do not commit:

- passwords, API keys, tokens, certificates, cookies, or connection strings;
- account identifiers or private user/customer data;
- proprietary SDK binaries, headers, generated code, or copied vendor documentation without a compatible license;
- production database names, topology, internal hostnames, filesystem paths, or operational secrets;
- private datasets, watchlists, research universes, positions, orders, or account state;
- strategy parameters, factor definitions, alpha logic, rankings, sizing, entry/exit rules, execution logic, arbitrage logic, or other trading-decision IP;
- source code whose copyright or license does not permit redistribution.

## Review rule

Every contribution that originated from experience with a private system should be reviewed by asking two separate questions:

1. **Is the capability generic and useful outside that system?**
2. **Does the public implementation reveal data, topology, proprietary material, or trading decision logic that is unnecessary to provide that capability?**

If the answer to the second question is yes or uncertain, keep it out of the public repository and implement a narrower public abstraction instead.
