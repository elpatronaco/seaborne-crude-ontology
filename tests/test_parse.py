# MIT License — Copyright (c) 2026 Pau Colomé
"""Phase 1 validation tests: Turtle parsing, module metadata, and ROBOT/HermiT smoke test."""

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_DIR = ROOT / "ontology"
CATALOG_PATH = ONTOLOGY_DIR / "catalog-v001.xml"
INTEGRATOR_PATH = ONTOLOGY_DIR / "seaborne-crude.ttl"
ROBOT_BIN = ROOT / "tools" / "robot"

SC = Namespace("https://w3id.org/seaborne-crude#")
CC_BY_4_0 = URIRef("https://creativecommons.org/licenses/by/4.0/")

DOMAIN_MODULES = [
    ONTOLOGY_DIR / name
    for name in (
        "core-contract.ttl",
        "incoterms.ttl",
        "logistics.ttl",
        "quality.ttl",
        "seaborne-crude.ttl",
    )
]

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


@pytest.mark.parametrize("module_path", DOMAIN_MODULES, ids=lambda p: p.name)
def test_bilingual_annotations_complete(module_path: Path) -> None:
    """Every first-party sc: class, property, and named individual must have @en/@es label and definition."""
    graph = Graph()
    graph.parse(module_path, format="turtle")

    sc_prefix = str(SC)
    entity_types = {
        OWL.Class,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.NamedIndividual,
        OWL.FunctionalProperty,
    }
    entities = {
        s
        for t in entity_types
        for s in graph.subjects(RDF.type, t)
        if isinstance(s, URIRef) and str(s).startswith(sc_prefix)
    }

    for entity in sorted(entities, key=str):
        types = set(graph.objects(entity, RDF.type))
        if OWL.FunctionalProperty in types:
            assert OWL.ObjectProperty in types or OWL.DatatypeProperty in types, (
                f"{entity} in {module_path.name} is owl:FunctionalProperty without ObjectProperty/DatatypeProperty"
            )

        label_langs = {
            lbl.language for lbl in graph.objects(entity, RDFS.label) if isinstance(lbl, Literal)
        }
        assert {"en", "es"}.issubset(label_langs), (
            f"{entity} in {module_path.name} missing @en/@es rdfs:label (found: {label_langs})"
        )

        def_langs = {
            d.language for d in graph.objects(entity, SKOS.definition) if isinstance(d, Literal)
        }
        assert {"en", "es"}.issubset(def_langs), (
            f"{entity} in {module_path.name} missing @en/@es skos:definition (found: {def_langs})"
        )


def test_offline_imports_mapped_in_catalog() -> None:
    """Every owl:imports across first-party modules must resolve locally via catalog-v001.xml."""
    tree = ET.parse(CATALOG_PATH)
    ns = {"cat": "urn:oasis:names:tc:entity:xmlns:xml:catalog"}
    catalog_map = {
        elem.attrib["name"]: ONTOLOGY_DIR / elem.attrib["uri"]
        for elem in tree.findall(".//cat:uri", ns)
    }

    for module_path in FIRST_PARTY_MODULES:
        graph = Graph()
        graph.parse(module_path, format="turtle")
        for imp in graph.objects(predicate=OWL.imports):
            imp_str = str(imp)
            assert imp_str in catalog_map, (
                f"{module_path.name} imports unmapped IRI {imp_str}"
            )
            assert catalog_map[imp_str].exists(), (
                f"Catalog target for {imp_str} does not exist: {catalog_map[imp_str]}"
            )


def test_tbox_satisfiability_and_alignments(tmp_path: Path) -> None:
    """HermiT over seaborne-crude.ttl must find zero unsatisfiable sc: classes and infer external alignments."""
    out_ttl = tmp_path / "tbox_inferred.ttl"
    result = subprocess.run(
        [
            str(ROBOT_BIN),
            "reason",
            "--catalog",
            str(CATALOG_PATH),
            "--reasoner",
            "hermit",
            "--axiom-generators",
            "SubClass EquivalentClass",
            "--include-indirect",
            "true",
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

    g = Graph()
    g.parse(out_ttl, format="turtle")

    sc_prefix = str(SC)
    unsat = [
        str(s)
        for s in set(g.subjects(OWL.equivalentClass, OWL.Nothing))
        | set(g.subjects(RDFS.subClassOf, OWL.Nothing))
        if isinstance(s, URIRef) and str(s).startswith(sc_prefix)
    ]
    assert unsat == [], f"Unsatisfiable sc: classes found: {unsat}"

    expected_alignments = [
        (SC.CargoQuantity, URIRef("http://qudt.org/schema/qudt/QuantityValue")),
        (SC.QuantityUnit, URIRef("http://qudt.org/schema/qudt/Unit")),
        (
            SC.PhysicalCrudeContract,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/BilateralContract"),
        ),
        (
            SC.PhysicalCrudeContract,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/WrittenContract"),
        ),
        (
            SC.ContractDocument,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/ContractDocument"),
        ),
        (
            SC.IncotermRule,
            URIRef(
                "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/StandardizedTerms"
            ),
        ),
        (
            SC.QualitySpecification,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/ContractualElement"),
        ),
        (
            SC.GuaranteedSpecification,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/ContractualCommitment"),
        ),
        (
            SC.TypicalSpecification,
            URIRef("https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/NonBindingTerm"),
        ),
        (SC.Party, URIRef("https://www.omg.org/spec/Commons/PartiesAndSituations/Party")),
    ]
    for sc_cls, ext_cls in expected_alignments:
        assert (sc_cls, RDFS.subClassOf, ext_cls) in g, (
            f"Missing inferred alignment: {sc_cls} rdfs:subClassOf {ext_cls}"
        )
