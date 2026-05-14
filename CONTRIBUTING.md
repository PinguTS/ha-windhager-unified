# Contributing to Windhager Unified

Thank you for your interest in contributing. This document explains how to run checks
locally, what the PR review criteria are, and how to report issues.

## Prerequisites

All validation runs **inside Docker** — no host Python installation is needed.

```bash
make build          # build the test image (first time or after dependency changes)
make check          # ruff lint + black format-check + pytest
make format         # auto-format with black
make build-docs     # regenerate docs/integrator/rest-api.md and swagger-coverage.md
make shell          # interactive shell inside the container
```

The `make check` target runs exactly what CI runs on every pull request.

## Pre-commit hook (optional)

```bash
make install-git-hooks   # sets core.hooksPath to .githooks
```

After this, `git commit` runs `make check` automatically.

## Pull request expectations

- **Run `make check` before opening a PR.** CI must pass.
- **Keep changes focused.** One logical change per PR; avoid unrelated refactors in the
  same diff.
- **Extend tests for changed behavior.** Every new or modified code path must have
  corresponding tests. See `tests/` for patterns.
- **Do not invent API semantics.** All endpoint paths, HTTP methods, request/response
  schemas, and LON OID meanings must be traceable to `docs/swagger/` (Swagger 1.2
  source files) or documented with an explicit ASSUMPTION comment. See
  `.cursor/rules/api-source-of-truth.mdc` for the full policy.
- **No secrets or device-specific data.** Do not commit hosts, IPs, neuron IDs, program
  IDs, usernames, passwords, or any site-specific identifiers.

## Running targeted tests

```bash
docker compose run --rm test pytest tests/test_api_client.py -v
docker compose run --rm test pytest tests/ -k "test_config_flow" -v
```

## Documentation

If you update an API endpoint or add a new one, regenerate the reference docs:

```bash
make build-docs
```

Commit the regenerated `docs/integrator/rest-api.md` and
`docs/integrator/swagger-coverage.md` together with your change.

## Reporting issues

Please use the GitHub Issues tab. Before opening a bug report:

- Download a **Diagnostics** file from **Settings → Devices & Services →
  Windhager Unified → three-dot menu → Download diagnostics**.
- **Redact** all hostnames, IP addresses, and credentials from any log output before
  pasting.
- Include your Home Assistant version and the integration version.

For security issues, **do not open a public issue**. See [SECURITY.md](SECURITY.md).
