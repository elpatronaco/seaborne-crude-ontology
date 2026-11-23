# MIT License — Copyright (c) 2026 Pau Colomé
"""HermiT classification tests for Incoterms defined contract classes (CQ01, CQ02, CQ05, CQ07)."""

from pathlib import Path
import subprocess

from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "ontology" / "catalog-v001.xml"
ROBOT_BIN = ROOT / "tools" / "robot"

SC = Namespace("https://w3id.org/seaborne-crude#")
EX = Namespace("https://example.org/test-incoterms#")

INCOTERM_DEFINED_CLASSES = {
    SC.BuyerTransitRiskContract,
    SC.SellerTransitRiskContract,
    SC.BuyerFreightContract,
    SC.SellerFreightContract,
    SC.SellerInsuredContract,
    SC.BuyerVesselNominationContract,
    SC.SellerVesselNominationContract,
    SC.SellerFreightAndTransitRiskContract,
}


def test_incoterms_hermit_classification(tmp_path: Path) -> None:
    """HermiT must classify FOB, CFR, CIF, and DAP contracts into the exact obligation classes."""
    abox_path = tmp_path / "incoterms_abox.ttl"
    inferred_path = tmp_path / "incoterms_inferred.ttl"

    abox_ttl = """@prefix ex: <https://example.org/test-incoterms#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sc: <https://w3id.org/seaborne-crude#> .

<https://example.org/test-incoterms> a owl:Ontology ;
    owl:imports <https://w3id.org/seaborne-crude> .

ex:contract_fob a sc:SpotContract ;
    sc:hasIncotermRule sc:FOB .

ex:contract_cfr a sc:SpotContract ;
    sc:hasIncotermRule sc:CFR .

ex:contract_cif a sc:SpotContract ;
    sc:hasIncotermRule sc:CIF .

ex:contract_dap a sc:SpotContract ;
    sc:hasIncotermRule sc:DAP .
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
        str(s)
        for s in set(g.subjects(OWL.equivalentClass, OWL.Nothing))
        | set(g.subjects(RDFS.subClassOf, OWL.Nothing))
        if isinstance(s, URIRef) and str(s).startswith(sc_prefix)
    ]
    assert unsat == [], f"Unsatisfiable sc: classes found: {unsat}"

    # Composite class subsumption (CQ05)
    assert (SC.SellerFreightAndTransitRiskContract, RDFS.subClassOf, SC.SellerFreightContract) in g
    assert (SC.SellerFreightAndTransitRiskContract, RDFS.subClassOf, SC.SellerTransitRiskContract) in g

    # Exact obligation matrix over the 8 defined classes
    expected: dict[URIRef, set[URIRef]] = {
        EX.contract_fob: {
            SC.BuyerTransitRiskContract,
            SC.BuyerFreightContract,
            SC.BuyerVesselNominationContract,
        },
        EX.contract_cfr: {
            SC.BuyerTransitRiskContract,
            SC.SellerFreightContract,
            SC.SellerVesselNominationContract,
        },
        EX.contract_cif: {
            SC.BuyerTransitRiskContract,
            SC.SellerFreightContract,
            SC.SellerVesselNominationContract,
            SC.SellerInsuredContract,
        },
        EX.contract_dap: {
            SC.SellerTransitRiskContract,
            SC.SellerFreightContract,
            SC.SellerVesselNominationContract,
            SC.SellerFreightAndTransitRiskContract,
        },
    }

    for contract, expected_classes in expected.items():
        actual_classes = set(g.objects(contract, RDF.type)) & INCOTERM_DEFINED_CLASSES
        assert actual_classes == expected_classes, (
            f"Mismatch for {contract}: got {actual_classes}, expected {expected_classes}"
        )
