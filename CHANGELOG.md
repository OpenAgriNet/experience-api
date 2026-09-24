# Changelog

All notable changes to this project are recorded here, in the format of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
`MAJOR.MINOR.PATCH`, as `CONVENTIONS.md` sets out.

## [Unreleased]

### Added
- `EXPERIENCE_API_DSS_MODE=http` calls the real DSS: the §7 request, its event stream read leniently.
- A Dockerfile and a compose file that run the API with a healthcheck.
- `POST /v1/chat`: SSE or JSON by `Accept`, answered by a fake DSS for now.
- The repo skeleton: uv, ruff, pyright, vulture, pytest, pre-commit and CI.
- `create_app()`, the composition root.
- `GET /healthz`, for Docker and the front proxy.
- A test that enforces the architecture's dependency rule.
- ADR-0001, the architecture; the API contract, now owned here.
- `CLAUDE.md` and `CONVENTIONS.md`.
