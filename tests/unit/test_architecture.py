"""Architecture checks that protect the business layer before routes are added."""

import ast
from pathlib import Path

import launchkit.generation as generation
from launchkit.generation.briefing import BriefService
from launchkit.generation.html_generation import HtmlGenerationService
from launchkit.generation.mockups import MockupGenerationService
from launchkit.generation.page_builder import PageBuildService
from launchkit.generation.site_copy import SiteCopyExtractor
from launchkit.planning.service import SitePlanningService

PACKAGE_ROOT = Path(__file__).parents[2] / "src" / "launchkit"


def test_fastapi_is_limited_to_transport_modules() -> None:
    violations: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = path.relative_to(PACKAGE_ROOT)
        # main.py, api/, and auth/ are transport modules; FastAPI stays out of business logic.
        if relative == Path("main.py") or relative.parts[0] in {"api", "auth"}:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        )
        if any(name == "fastapi" or name.startswith("fastapi.") for name in imports):
            violations.append(str(relative))

    assert violations == []


def test_generation_public_api_exposes_callable_workflows() -> None:
    expected = {
        "LegacyBriefService",
        "WebsiteGenerationRequest",
        "WebsiteGenerationService",
    }

    assert expected <= set(generation.__all__)
    assert len(generation.__all__) == len(set(generation.__all__))
    assert all(hasattr(generation, name) for name in expected)


def test_staged_services_have_stable_explicit_imports() -> None:
    services = (
        BriefService,
        HtmlGenerationService,
        MockupGenerationService,
        PageBuildService,
        SiteCopyExtractor,
        SitePlanningService,
    )

    assert all(service.__module__.startswith("launchkit.") for service in services)
