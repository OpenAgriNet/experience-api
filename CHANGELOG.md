# Changelog

All notable changes to this project are recorded here, in the format of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
`MAJOR.MINOR.PATCH`, as `CONVENTIONS.md` sets out.

## [Unreleased]

### Added
- The repo skeleton: uv, ruff, pyright, vulture, pytest, pre-commit and CI.
- `create_app()`, the composition root.
- `GET /healthz`, for Docker and the front proxy.
- A test that enforces the architecture's dependency rule.
