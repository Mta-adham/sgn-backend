"""Guards the two hand-maintained copies of the member vocabularies.

The canonical industry and category lists live in app/core/, and sbn-website keeps a
mirror in src/memberCategories.js to drive its pickers without a round trip. The backend
validates against its own copy and *silently drops* anything it does not recognise
(normalise_industries / normalise_categories), so a value added to the frontend alone
does not error - it just vanishes on save, leaving a member with a missing field and no
indication why.

These tests fail loudly on that divergence instead. They are skipped rather than failed
when the frontend is not checked out beside the backend, so the suite still runs in CI
for this repo alone.
"""

import json
import re
from pathlib import Path

import pytest

from app.core.categories import MEMBER_CATEGORIES
from app.core.industries import INDUSTRY_DEFINITIONS

FRONTEND_VOCABULARY = (
    Path(__file__).resolve().parents[2] / "sbn-website" / "src" / "memberCategories.js"
)

pytestmark = pytest.mark.skipif(
    not FRONTEND_VOCABULARY.exists(),
    reason=f"sbn-website not checked out at {FRONTEND_VOCABULARY}",
)


def _frontend_source() -> str:
    return FRONTEND_VOCABULARY.read_text(encoding="utf-8")


def _parse_frontend_categories() -> list[str]:
    block = re.search(r"MEMBER_CATEGORIES\s*=\s*\[(.*?)\]", _frontend_source(), re.DOTALL)
    assert block, f"Could not find MEMBER_CATEGORIES in {FRONTEND_VOCABULARY}"
    return re.findall(r"['\"]([^'\"]+)['\"]", block.group(1))


def _parse_frontend_industries() -> list[dict]:
    block = re.search(
        r"INDUSTRY_DEFINITIONS\s*=\s*\[(.*?)\n\];", _frontend_source(), re.DOTALL
    )
    assert block, f"Could not find INDUSTRY_DEFINITIONS in {FRONTEND_VOCABULARY}"

    entries = []
    for raw in re.finditer(
        r"\{\s*name:\s*['\"](?P<name>[^'\"]+)['\"]\s*,\s*"
        r"group:\s*['\"](?P<group>[^'\"]+)['\"]\s*,\s*"
        r"vision2030:\s*(?P<vision>true|false)",
        block.group(1),
    ):
        entries.append(
            {
                "name": raw.group("name"),
                "group": raw.group("group"),
                "vision_2030": raw.group("vision") == "true",
            }
        )

    assert entries, "Parsed zero industries from the frontend; the format likely changed"
    return entries


def test_categories_match_frontend() -> None:
    assert _parse_frontend_categories() == MEMBER_CATEGORIES, (
        "MEMBER_CATEGORIES has drifted from sbn-website's copy. A category the backend "
        "does not recognise is dropped silently on save."
    )


def test_industry_names_match_frontend() -> None:
    frontend = [entry["name"] for entry in _parse_frontend_industries()]
    backend = [entry["name"] for entry in INDUSTRY_DEFINITIONS]

    only_frontend = sorted(set(frontend) - set(backend))
    only_backend = sorted(set(backend) - set(frontend))

    assert not only_frontend, (
        f"Industries in sbn-website but not the backend: {only_frontend}. "
        "Members can select these and the backend will silently discard them."
    )
    assert not only_backend, (
        f"Industries in the backend but not sbn-website: {only_backend}. "
        "These are valid but no member can ever pick them."
    )
    assert frontend == backend, "Industry ordering differs; the pickers will not match."


def test_industry_groups_and_vision_flags_match_frontend() -> None:
    frontend = _parse_frontend_industries()
    backend = [
        {"name": e["name"], "group": e["group"], "vision_2030": e["vision_2030"]}
        for e in INDUSTRY_DEFINITIONS
    ]

    mismatches = [
        {"frontend": f, "backend": b} for f, b in zip(frontend, backend, strict=True) if f != b
    ]
    assert not mismatches, (
        "Industry group or Vision 2030 flag differs between frontend and backend:\n"
        + json.dumps(mismatches, indent=2)
    )
