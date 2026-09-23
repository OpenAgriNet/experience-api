# Conventions

Naming, versioning, git workflow, logging and linting. Copied from the DSS repo
so people move between the two without relearning; changed only where this repo
differs.

## Naming

### Python
| Artifact | Convention | Example |
|---|---|---|
| Module | `snake_case.py` | `service.py` |
| Class | `PascalCase` noun | `ChatTurn` |
| Function | `snake_case` verb | `to_chat_turn` |
| Constant | `UPPER_SNAKE_CASE` | `SSE_MEDIA_TYPE` |
| Type alias | `PascalCase` | `LanguageCode = str` |

### API and contract
- **The wire is camelCase; Python is snake_case.** Aliases bridge the two only
  in each adapter's `schemas.py`. Nothing inward sees a camelCase name.
- Language codes: BCP 47 only (`gu`, `hi`, `en`), never full names.
- Channel values: lowercase (`web`, `whatsapp`, `voice`).
- IDs: always `str`, never `int`.
- History roles: `"user"` or `"assistant"` only.
- API versioning: a new path version (`/v2`) on a breaking change, never a
  suffixed field name.

### Environment variables
`UPPER_SNAKE_CASE`, prefix `EXPERIENCE_API_`. Booleans: `true` / `false` only.
```
EXPERIENCE_API_FAKE_SCENARIO=busy
EXPERIENCE_API_DSS_BASE_URL=http://localhost:8077
```

## Versioning
`MAJOR.MINOR.PATCH`, single source of truth in `pyproject.toml`.

| Bump | When |
|---|---|
| MAJOR | Breaking contract change |
| MINOR | New backwards-compatible capability |
| PATCH | Bug fix, no contract change |

Release tags: annotated, on `main` only, immutable once pushed.

## Changelog
`CHANGELOG.md` at the repo root, `[Unreleased]` section always present.

## Git workflow

### Branches
`{type}/{short-description}`, e.g. `feat/chat-answered-slice`. Add the issue
number (`feat/42-...`) once this repo has an issue tracker.

### Commit messages
`<type>: <summary in imperative mood>`. Add ` [#<issue-no>]` once there is a
tracker.

**Keep it minimal.** The subject is usually the whole message. Add a body only
when *why* is not obvious from the diff: bullet points, one line each, at most
five. Reasoning that needs more belongs in an ADR or the PR body.

| Type | When | Version impact |
|---|---|---|
| feat | New capability | MINOR |
| fix | Bug fix | PATCH |
| refactor | No behaviour change | None |
| chore | Tooling, deps | None |
| test | Tests only | None |
| docs | Docs only | None |

`BREAKING CHANGE:` in the footer means a MAJOR bump regardless of type.

### Pull requests
- Title: Conventional Commits, like a commit subject.
- Body: `What`, `Why`, `Testing`. End with `Relates to #<issue-no>` once there
  is a tracker.
- A PR is one logical step with a handful of commits, each green on its own.

### Merge strategy
Rebase merge. Each commit lands on `main` individually. Squash within a branch
for cleanup; never squash the whole PR on merge.

## Logging
Include the `transaction_id` once a turn has one. Never log a user's query,
history or location.
```python
logger.info("transaction_id=%s dss_status=%s", transaction_id, status)
```
Levels: `DEBUG` internal state · `INFO` turn lifecycle · `WARNING` recoverable
failure · `ERROR` unrecoverable failure.

## Linting, types and dead code
- **ruff** for lint and format, same config as the DSS.
- **pyright** in `standard` mode.
- **vulture** for dead code; false positives go in `vulture_whitelist.py`.
- pre-commit runs all three on every commit and the tests before every push.
  CI runs everything again, since hooks can be skipped with `--no-verify`.
