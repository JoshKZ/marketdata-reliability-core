# Security Policy

## Reporting a vulnerability

Please do not publish credentials, tokens, private datasets, proprietary vendor material, or exploit details in a public GitHub issue.

For a vulnerability in this repository, use GitHub's private vulnerability reporting feature when available. If private reporting is unavailable, open a minimal public issue that contains no sensitive details and asks the maintainer for a private contact path.

## Scope

Security reports may include issues such as:

- unsafe parsing or deserialization;
- path or command injection introduced by project code;
- accidental secret exposure;
- dependency or packaging problems that materially affect users;
- correction or provenance behavior that could silently corrupt data.

This project does not provide brokerage login, order submission, account management, or custody functionality.

## Offline CLI threat model

The CLI reads caller-selected local UTF-8 CSV files, uses strict column/row and
timestamp checks, parses numeric cells as Decimal, and applies explicit input and
expected-grid bounds. It does not evaluate code, load pickle objects, follow URLs,
execute subprocesses during an audit, or contact a provider. Parsing diagnostics
identify records and fields without echoing cell contents.

Bounds protect ordinary batch usage; they are not a hard process-memory quota or
a sandbox for hostile filesystems. File paths and destination directories must be
trusted. Do not expose the CLI as a multi-tenant upload service without additional
application-level isolation, access control, and resource limits.

`--output` exclusively creates a new file only after parsing/auditing/serialization
succeed. Existing paths are not overwritten by this option. A filesystem write
failure can still leave an incomplete newly created output: this is not a durable
atomic transaction. Exit 2 means the output must not be consumed as a completed
audit. Shell redirection is outside the application's no-overwrite protection.

Reports do not automatically include raw OHLCV, source payloads, or local paths,
but instrument identities and caller-supplied messages may be sensitive. The JSON
serializer is not a general-purpose redaction or authentication mechanism. Review
reports before sharing and treat strings as untrusted in downstream renderers.

There are no third-party runtime dependencies. Build/development tools and GitHub
Actions still form a software supply chain. CI actions are commit-pinned, use
read-only repository permissions, and do not persist checkout credentials.
Automated checks and agent-assisted review are not an independent security audit.
