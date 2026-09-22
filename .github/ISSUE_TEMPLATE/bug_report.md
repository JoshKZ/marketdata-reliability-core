---
name: Bug report
about: Report a reproducible correctness, installation, or CLI problem
title: ''
labels: ''
assignees: ''
---

## Environment
Package version or commit, Python version, operating system, and installation method:

## Expected behavior

## Observed behavior
Include the exit code for CLI problems. Do not treat a completed audit with findings
(exit 1) as a parser crash (exit 2).

## Minimal synthetic reproduction
Provide the smallest synthetic CSV or Python example that reproduces the issue.
Remove account identifiers, API keys, tokens, private datasets, local paths, and
proprietary vendor material. Review instrument names and report messages too.

For a potential vulnerability, follow SECURITY.md instead of disclosing exploit
details in this public issue.
