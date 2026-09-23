"""The package is installed as a distribution, not just found on sys.path.

Guards the build config in `pyproject.toml`: `src/experience_api` does not match
the distribution name, so the wheel's package path is declared by hand, and a
typo there would still let `import experience_api` work from the source tree
while the built image shipped nothing.
"""

from importlib.metadata import version


def test_distribution_is_installed() -> None:
    assert version("experience-api")
