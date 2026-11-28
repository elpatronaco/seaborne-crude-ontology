# MIT License — Copyright (c) 2026 Pau Colomé
"""HermiT EIA classification boundary tests for quality.ttl (CQ14)."""

from pathlib import Path
import subprocess

from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "ontology" / "catalog-v001.xml"
ROBOT_BIN = ROOT / "tools" / "robot"

SC = Namespace("https://w3id.org/seaborne-crude#")
EX = Namespace("https://example.org/test-quality#")

API_CLASSES = {
    SC.HeavyCrudeCargo,
    SC.IntermediateCrudeCargo,
    SC.LightCrudeCargo,
}

SULFUR_CLASSES = {
    SC.SweetCrudeCargo,
    SC.SourCrudeCargo,
}


def test_quality_hermit_eia_classification(tmp_path: Path) -> None:
    """HermiT must classify cargoes into disjoint EIA API and sulfur classes at exact boundaries."""
    abox_path = tmp_path / "quality_abox.ttl"
    inferred_path = tmp_path / "quality_inferred.ttl"

    abox_ttl = """@prefix ex: <https://example.org/test-quality#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sc: <https://w3id.org/seaborne-crude#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org/test-quality> a owl:Ontology ;
    owl:imports <https://w3id.org/seaborne-crude> .

ex:cargo_heavy_21_9 a sc:Cargo ;
    sc:measuredAPIGravity "21.9"^^xsd:decimal ;
    sc:measuredSulfurContent "0.50"^^xsd:decimal .

ex:cargo_heavy_22_0 a sc:Cargo ;
    sc:measuredAPIGravity "22.0"^^xsd:decimal ;
    sc:measuredSulfurContent "0.51"^^xsd:decimal .

ex:cargo_inter_22_1 a sc:Cargo ;
    sc:measuredAPIGravity "22.1"^^xsd:decimal .

ex:cargo_inter_38_0 a sc:Cargo ;
    sc:measuredAPIGravity "38.0"^^xsd:decimal ;
    sc:measuredSulfurContent "0.14"^^xsd:decimal .

ex:cargo_light_38_1 a sc:Cargo ;
    sc:measuredAPIGravity "38.1"^^xsd:decimal ;
    sc:measuredSulfurContent "1.20"^^xsd:decimal .
"""
    abox_path.write_text(abox_ttl, encoding="utf-8")

    result = subprocess.run(
        [
            str(ROBOT_BIN),
            "reason",
            "--catalog",
            str(CATALOG_PATH),
            "--reasoner",
            "hermit",
            "--axiom-generators",
            "SubClass EquivalentClass ClassAssertion",
            "--include-indirect",
            "true",
            "--input",
            str(abox_path),
            "--output",
            str(inferred_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"ROBOT HermiT failed (rc={result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    g = Graph()
    g.parse(inferred_path, format="turtle")

    # Zero unsatisfiable sc: classes
    sc_prefix = str(SC)
    unsat = [
        cls
        for cls in g.subjects(RDFS.subClassOf, OWL.Nothing)
        if isinstance(cls, URIRef) and str(cls).startswith(sc_prefix)
    ]
    assert not unsat, f"Unsatisfiable sc: classes found: {unsat}"

    # API gravity boundary assertions
    expected_api = {
        EX.cargo_heavy_21_9: SC.HeavyCrudeCargo,
        EX.cargo_heavy_22_0: SC.HeavyCrudeCargo,
        EX.cargo_inter_22_1: SC.IntermediateCrudeCargo,
        EX.cargo_inter_38_0: SC.IntermediateCrudeCargo,
        EX.cargo_light_38_1: SC.LightCrudeCargo,
    }
    for cargo, expected_cls in expected_api.items():
        types = set(g.objects(cargo, RDF.type))
        assert expected_cls in types, f"{cargo} missing {expected_cls}: {types}"
        assert (types & API_CLASSES) == {expected_cls}, (
            f"{cargo} has unexpected API classes: {types & API_CLASSES}"
        )

    # Sulfur boundary assertions (orthogonal to API)
    expected_sulfur = {
        EX.cargo_heavy_21_9: SC.SweetCrudeCargo,
        EX.cargo_heavy_22_0: SC.SourCrudeCargo,
        EX.cargo_inter_38_0: SC.SweetCrudeCargo,
        EX.cargo_light_38_1: SC.SourCrudeCargo,
    }
    for cargo, expected_cls in expected_sulfur.items():
        types = set(g.objects(cargo, RDF.type))
        assert expected_cls in types, f"{cargo} missing {expected_cls}: {types}"
        assert (types & SULFUR_CLASSES) == {expected_cls}, (
            f"{cargo} has unexpected sulfur classes: {types & SULFUR_CLASSES}"
        )
