"""Names vulture must not report as dead.

One `_.<name>` line per entry, with a comment saying who really uses it: a
framework hook, a pytest fixture found by name, a Protocol method only its
implementations define. `uv run vulture --make-whitelist` prints lines in this
format for everything it currently flags. Copy over only real false positives.

To every other tool this file is a useless expression on an undefined name, by
design. Ruff ignores B018 and F821 here, and the file sits outside pyright's
`include`.
"""
