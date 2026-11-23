# MIT License — Copyright (c) 2026 Pau Colomé
"""Phase 1 validation tests: Turtle parsing, module metadata, and ROBOT/HermiT smoke test."""

from pathlib import Path
import subprocess

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_DIR = ROOT / "ontology"
CATALOG_PATH = ONTOLOGY_DIR / "catalog-v001.xml"
INTEGRATOR_PATH = ONTOLOGY_DIR / "seaborne-crude.ttl"
ROBOT_BIN = ROOT / "tools" / "robot"

CC_BY_4_0 = URIRef("https://creativecommons.org/licenses/by/4.0/")

FIRST_PARTY_MODULES = sorted(ONTOLOGY_DIR.glob("*.ttl"))
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


@pytest.mark.parametrize("module_path", FIRST_PARTY_MODULES, ids=lambda p: p.name)
def test_first_party_module_metadata(module_path: Path) -> None:
    """Every first-party module must declare owl:Ontology, versionIRI, CC BY 4.0, and @en/@es titles."""
    graph = Graph()
    graph.parse(module_path, format="turtle")

    ontologies = list(graph.subjects(RDF.type, OWL.Ontology))
    assert len(ontologies) == 1, f"{module_path.name} must declare exactly one owl:Ontology"
    onto = ontologies[0]

    version_iris = list(graph.objects(onto, OWL.versionIRI))
    assert len(version_iris) == 1, f"{module_path.name} must declare owl:versionIRI"

    licenses = list(graph.objects(onto, DCTERMS.license))
    assert CC_BY_4_0 in licenses, f"{module_path.name} must declare CC BY 4.0 license"

    titles = list(graph.objects(onto, DCTERMS.title))
    langs = {t.language for t in titles if isinstance(t, Literal)}
    assert {"en", "es"}.issubset(langs), f"{module_path.name} must have dcterms:title in @en and @es"


def test_integrator_imports() -> None:
    """seaborne-crude.ttl must import the 5 active Iteration 1 modules and defer entities.ttl."""
    graph = Graph()
    graph.parse(INTEGRATOR_PATH, format="turtle")

    onto = URIRef("https://w3id.org/seaborne-crude")
    imports = set(graph.objects(onto, OWL.imports))

    expected_imports = {
        URIRef("https://w3id.org/seaborne-crude/core-contract"),
        URIRef("https://w3id.org/seaborne-crude/incoterms"),
        URIRef("https://w3id.org/seaborne-crude/logistics"),
        URIRef("https://w3id.org/seaborne-crude/quality"),
        URIRef("https://w3id.org/seaborne-crude/alignments"),
    }
    assert expected_imports.issubset(imports)
    assert URIRef("https://w3id.org/seaborne-crude/entities") not in imports


def test_robot_hermit_reasoner_smoke(tmp_path: Path) -> None:
    """ROBOT with HermiT must load the catalog-resolved integrator ontology and classify cleanly."""
    assert ROBOT_BIN.exists(), f"ROBOT wrapper not found at {ROBOT_BIN}; run scripts/install_robot.sh"
    out_ttl = tmp_path / "inferred.ttl"

    result = subprocess.run(
        [
            str(ROBOT_BIN),
            "reason",
            "--catalog",
            str(CATALOG_PATH),
            "--reasoner",
            "hermit",
            "--input",
            str(INTEGRATOR_PATH),
            "--output",
            str(out_ttl),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"ROBOT HermiT failed (rc={result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert out_ttl.exists() and out_ttl.stat().st_size > 0

    inferred = Graph()
    inferred.parse(out_ttl, format="turtle")
    assert len(inferred) > 0
