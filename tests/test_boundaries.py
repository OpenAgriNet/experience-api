"""The dependency rule, enforced.

The rule is §4.1 of the architecture (`docs/ADR/0001-architecture.md`). Features
sit at the top and keep their layers inside, so the folders no longer show the
layers. This test does. Every module under `src/experience_api` is placed in a
layer by its path, and each import is checked against what that layer may use.
A module that fits no layer fails too, so a stray `chat/util.py` or a new root
module is caught.

What each layer may import, beyond the standard library:

- `app.py` and the package `__init__`: anything. They are the composition root.
- `settings.py`: pydantic, pydantic_settings.
- `shared/**`: pydantic, fastapi, starlette, and other `shared` modules.
- `<feature>/__init__.py`: anything in its own feature. What it re-exports is
  the feature's public face.
- `<feature>/domain.py`: pydantic.
- `<feature>/service.py`, `ports.py`: their own `domain` and `ports`, nothing
  else. Config reaches a service as plain constructor arguments, never as
  `Settings`, so only `app.py` reads settings.
- `<feature>/adapters/<name>/**`: any third party; the feature's own `domain`
  and `ports`; siblings in the same `adapters/<name>`; `shared`; and another
  feature's package itself (`experience_api.auth`), never its insides.

Imports are read from the AST, never executed. A relative import is resolved to
its absolute name first. `from pkg import mod` counts as importing `pkg.mod`
when `mod` is a module. String literals passed to `import_module` or
`__import__` are checked too.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

PACKAGE = "experience_api"
SRC = Path(__file__).resolve().parents[1] / "src" / PACKAGE

STDLIB = frozenset(sys.stdlib_module_names)
ROOT_MODULES = frozenset({"app", "settings", "shared"})


@dataclass(frozen=True)
class Layer:
    name: str
    # Top-level packages outside ours it may import. None means any.
    third_party: frozenset[str] | None
    # Our modules it may import, relative to the package. "x.*" is x and below.
    internal: tuple[str, ...]
    # Whether another feature's package itself may be imported.
    other_features: bool = False


def classify(module: tuple[str, ...], is_package: bool) -> Layer | None:
    """The layer a module is in, or None when the layout has no place for it."""

    if module in ((), ("app",)):
        return Layer("app", None, ("*",))
    if module == ("settings",):
        return Layer("settings", frozenset({"pydantic", "pydantic_settings"}), ())
    if module[0] == "shared":
        return Layer(
            "shared", frozenset({"pydantic", "fastapi", "starlette"}), ("shared.*",)
        )

    feature = module[0]
    if len(module) == 1:
        return Layer("feature", None, (f"{feature}.*",)) if is_package else None
    if module[1:] == ("domain",):
        return Layer("domain", frozenset({"pydantic"}), ())
    if module[1:] in (("service",), ("ports",)):
        return Layer("service", frozenset(), (f"{feature}.domain", f"{feature}.ports"))
    if module[1] == "adapters":
        own = [f"{feature}.domain", f"{feature}.ports", "shared.*"]
        if len(module) >= 3:
            own.append(f"{feature}.adapters.{module[2]}.*")
        return Layer("adapter", None, tuple(own), other_features=True)
    return None


def _is_module(name: str, src: Path, package: str) -> bool:
    parts = name.split(".")
    if parts[0] != package or len(parts) == 1:
        return False
    path = src.joinpath(*parts[1:])
    return path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()


def imported_names(
    tree: ast.AST, *, here: tuple[str, ...], src: Path, package: str
) -> set[str]:
    """Every absolute module name a module imports.

    `here` is the dotted package the module sits in, which a relative import is
    resolved against.
    """

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = here[: len(here) - node.level + 1] if node.level else ()
            prefix = ".".join((*base, node.module) if node.module else base)
            for alias in node.names:
                candidate = f"{prefix}.{alias.name}"
                names.add(candidate if _is_module(candidate, src, package) else prefix)
        elif isinstance(node, ast.Call):
            target = node.func
            dynamic = (isinstance(target, ast.Name) and target.id == "__import__") or (
                isinstance(target, ast.Attribute) and target.attr == "import_module"
            )
            if dynamic:
                names.update(
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                )
    return names


def _matches(target: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith(".*"):
        base = pattern[:-2]
        return target == base or target.startswith(base + ".")
    return target == pattern


def _allowed(name: str, layer: Layer, feature: str, package: str) -> bool:
    root = name.split(".")[0]
    if root in STDLIB:
        return True
    if root != package:
        return layer.third_party is None or root in layer.third_party
    target = name[len(package) + 1 :]
    if any(_matches(target, pattern) for pattern in layer.internal):
        return True
    return (
        layer.other_features
        and bool(target)
        and "." not in target
        and target != feature
        and target not in ROOT_MODULES
    )


def violations(src: Path, package: str = PACKAGE) -> list[str]:
    """Every forbidden import under `src`, as `path -> name: reason`."""

    found: list[str] = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src)
        is_package = path.name == "__init__.py"
        parts = rel.with_suffix("").parts
        module = parts[:-1] if is_package else parts
        layer = classify(module, is_package)
        if layer is None:
            found.append(f"{rel.as_posix()}: fits no layer")
            continue
        here = (package, *(module if is_package else module[:-1]))
        tree = ast.parse(path.read_text(), filename=str(path))
        feature = module[0] if module else ""
        for name in sorted(imported_names(tree, here=here, src=src, package=package)):
            if not _allowed(name, layer, feature, package):
                found.append(
                    f"{rel.as_posix()} -> {name}: {layer.name} may not import it"
                )
    return found


# ---------------------------------------------------------------------------
# The live tree.
# ---------------------------------------------------------------------------


def test_the_package_has_modules_to_check() -> None:
    assert list(SRC.rglob("*.py")), f"no modules under {SRC}; the rule is vacuous"


def test_every_module_obeys_the_dependency_rule() -> None:
    assert violations(SRC) == []


# ---------------------------------------------------------------------------
# The checker itself, on temporary trees. One tree that uses every allowance and
# must pass, then one case per way to break the rule.
# ---------------------------------------------------------------------------


def _tree(root: Path, files: dict[str, str]) -> Path:
    src = root / PACKAGE
    for rel, body in files.items():
        path = src / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return src


ALLOWED = {
    "__init__.py": "",
    "app.py": (
        "import httpx\n"
        f"from {PACKAGE}.chat import ChatService\n"
        f"from {PACKAGE}.chat.adapters.http import routes\n"
    ),
    "settings.py": "from pydantic_settings import BaseSettings\n",
    "shared/__init__.py": "",
    "shared/errors.py": (
        "from fastapi import FastAPI\n"
        "from starlette.exceptions import HTTPException\n"
        f"from {PACKAGE}.shared import ids\n"
    ),
    "shared/ids.py": "import uuid\n",
    "chat/__init__.py": f"from {PACKAGE}.chat.service import ChatService\n",
    "chat/domain.py": (
        "from dataclasses import dataclass\nfrom pydantic import BaseModel\n"
    ),
    "chat/ports.py": (
        f"from typing import Protocol\nfrom {PACKAGE}.chat.domain import X\n"
    ),
    "chat/service.py": "from .domain import X\nfrom .ports import DssClient\n",
    "chat/adapters/__init__.py": "",
    "chat/adapters/http/__init__.py": "",
    "chat/adapters/http/routes.py": (
        "from fastapi import APIRouter\n"
        f"from {PACKAGE}.auth import current_user\n"
        f"from {PACKAGE}.chat import domain\n"
        f"from {PACKAGE}.shared.errors import AppError\n"
        "from . import schemas\n"
    ),
    "chat/adapters/http/schemas.py": "",
    "auth/__init__.py": "",
}


def test_every_allowance_passes(tmp_path: Path) -> None:
    assert violations(_tree(tmp_path, ALLOWED)) == []


CHAT = {"chat/__init__.py": "", "chat/adapters/__init__.py": ""}
CHAT_HTTP = {**CHAT, "chat/adapters/http/__init__.py": ""}
CHAT_DSS = {
    **CHAT,
    "chat/adapters/dss/__init__.py": "",
    "chat/adapters/dss/fake.py": "",
}
AUTH = {
    "auth/__init__.py": "",
    "auth/service.py": "",
    "auth/adapters/__init__.py": "",
    "auth/adapters/http/__init__.py": "",
    "auth/adapters/http/routes.py": "",
}
SHARED = {"shared/__init__.py": "", "shared/errors.py": ""}

BREAKS = {
    "domain imports the framework": (
        {**CHAT, "chat/domain.py": "import fastapi\n"},
        "chat/domain.py -> fastapi: domain may not import it",
    ),
    "domain reaches shared by a relative import": (
        {**CHAT, **SHARED, "chat/domain.py": "from ..shared import errors\n"},
        f"chat/domain.py -> {PACKAGE}.shared.errors: domain may not import it",
    ),
    "service imports an adapter by a relative import": (
        {**CHAT_DSS, "chat/service.py": "from .adapters.dss import fake\n"},
        f"chat/service.py -> {PACKAGE}.chat.adapters.dss.fake: "
        "service may not import it",
    ),
    "service imports an adapter by name": (
        {**CHAT_DSS, "chat/service.py": f"import {PACKAGE}.chat.adapters.dss\n"},
        f"chat/service.py -> {PACKAGE}.chat.adapters.dss: service may not import it",
    ),
    "service imports an adapter dynamically": (
        {
            **CHAT_DSS,
            "chat/service.py": (
                "import importlib\n"
                f"importlib.import_module('{PACKAGE}.chat.adapters')\n"
            ),
        },
        f"chat/service.py -> {PACKAGE}.chat.adapters: service may not import it",
    ),
    "service imports a third-party package": (
        {**CHAT, "chat/service.py": "import httpx\n"},
        "chat/service.py -> httpx: service may not import it",
    ),
    "service reads Settings instead of taking plain values": (
        {
            **CHAT,
            "settings.py": "",
            "chat/service.py": f"from {PACKAGE} import settings\n",
        },
        f"chat/service.py -> {PACKAGE}.settings: service may not import it",
    ),
    "adapter reaches into another feature's adapters": (
        {
            **CHAT_HTTP,
            **AUTH,
            "chat/adapters/http/routes.py": (
                f"from {PACKAGE}.auth.adapters.http import routes\n"
            ),
        },
        f"chat/adapters/http/routes.py -> {PACKAGE}.auth.adapters.http.routes: "
        "adapter may not import it",
    ),
    "adapter reaches into another feature's service": (
        {
            **CHAT_HTTP,
            **AUTH,
            "chat/adapters/http/routes.py": f"from {PACKAGE}.auth import service\n",
        },
        f"chat/adapters/http/routes.py -> {PACKAGE}.auth.service: "
        "adapter may not import it",
    ),
    "one adapter bypasses the port to reach another": (
        {
            **CHAT_HTTP,
            **CHAT_DSS,
            "chat/adapters/http/routes.py": (
                f"from {PACKAGE}.chat.adapters.dss import fake\n"
            ),
        },
        f"chat/adapters/http/routes.py -> {PACKAGE}.chat.adapters.dss.fake: "
        "adapter may not import it",
    ),
    "shared imports a feature": (
        {
            **SHARED,
            **CHAT,
            "chat/domain.py": "",
            "shared/ids.py": (f"from {PACKAGE}.chat import domain\n"),
        },
        f"shared/ids.py -> {PACKAGE}.chat.domain: shared may not import it",
    ),
    "settings imports the framework": (
        {"settings.py": "import fastapi\n"},
        "settings.py -> fastapi: settings may not import it",
    ),
    "a feature module that fits no layer": (
        {**CHAT, "chat/util.py": ""},
        "chat/util.py: fits no layer",
    ),
    "a root module that fits no layer": (
        {"helpers.py": ""},
        "helpers.py: fits no layer",
    ),
}


@pytest.mark.parametrize(("files", "expected"), BREAKS.values(), ids=BREAKS.keys())
def test_each_break_is_caught(
    tmp_path: Path, files: dict[str, str], expected: str
) -> None:
    assert violations(_tree(tmp_path, files)) == [expected]
