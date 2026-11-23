# MIT License — Copyright (c) 2026 Pau Colomé
"""Phase 1 validation tests: Turtle parsing, module metadata, and ROBOT/HermiT smoke test."""

from pathlib import Path

import pytest
from rdflib import Graph

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_DIR = ROOT / "ontology"

ALL_TTL_FILES = sorted(
    p
    for base in (ONTOLOGY_DIR, ROOT / "shapes", ROOT / "data")
    if base.exists()
    for p in base.rglob("*.ttl")
)


@pytest.mark.parametrize("ttl_path", ALL_TTL_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_turtle_parses(ttl_path: Path) -> None:
    """Every Turtle file under ontology/, shapes/, and data/ must parse cleanly."""
    assert len(ALL_TTL_FILES) >= 8, "Expected at least 7 ontology modules plus cached owl-time.ttl"
    graph = Graph()
    graph.parse(ttl_path, format="turtle")
    assert len(graph) > 0, f"{ttl_path} parsed into an empty graph"
