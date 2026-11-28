# MIT License — Copyright (c) 2026 Pau Colomé
"""HermiT classification and OWL-Time hierarchy tests for logistics.ttl (CQ06, CQ08, CQ09, CQ10)."""

from pathlib import Path
import subprocess

from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "ontology" / "catalog-v001.xml"
ROBOT_BIN = ROOT / "tools" / "robot"

SC = Namespace("https://w3id.org/seaborne-crude#")
TIME = Namespace("http://www.w3.org/2006/time#")
EX = Namespace("https://example.org/test-logistics#")

AFRA_CLASSES = {
    SC.Aframax,
    SC.Suezmax,
    SC.VLCC,
}


def test_logistics_hermit_classification(tmp_path: Path) -> None:
    """HermiT must classify vessels by DWT into AFRA classes and Laycan under OWL-Time."""
    abox_path = tmp_path / "logistics_abox.ttl"
    inferred_path = tmp_path / "logistics_inferred.ttl"

    abox_ttl = """@prefix ex: <https://example.org/test-logistics#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sc: <https://w3id.org/seaborne-crude#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org/test-logistics> a owl:Ontology ;
    owl:imports <https://w3id.org/seaborne-crude> .

ex:v_afra a sc:Vessel ;
    sc:deadweightTonnage 100000.0 .

ex:v_suez a sc:Vessel ;
    sc:deadweightTonnage 150000.0 .

ex:v_vlcc a sc:Vessel ;
    sc:deadweightTonnage 280000.0 .

ex:v_below_afra a sc:Vessel ;
    sc:deadweightTonnage 79999.9 .

ex:v_afra_min a sc:Vessel ;
    sc:deadweightTonnage 80000.0 .

ex:v_afra_max a sc:Vessel ;
    sc:deadweightTonnage 119999.9 .

ex:v_suez_min a sc:Vessel ;
    sc:deadweightTonnage 120000.0 .

ex:v_suez_max a sc:Vessel ;
    sc:deadweightTonnage 199999.9 .

ex:v_vlcc_min a sc:Vessel ;
    sc:deadweightTonnage 200000.0 .

ex:port_ras_tanura a sc:Port .
ex:port_rotterdam a sc:Port .

ex:qty_loaded a sc:CargoQuantity ;
    sc:quantityValue 2000000.0 ;
    sc:hasQuantityUnit sc:Barrel .

ex:laycan_start a time:Instant ;
    time:inXSDDate "2026-05-10"^^xsd:date .

ex:laycan_end a time:Instant ;
    time:inXSDDate "2026-05-12"^^xsd:date .

ex:laycan1 a sc:Laycan ;
    time:hasBeginning ex:laycan_start ;
    time:hasEnd ex:laycan_end ;
    sc:laycanStartDate "2026-05-10"^^xsd:date ;
    sc:laycanEndDate "2026-05-12"^^xsd:date .

ex:cargo1 a sc:Cargo ;
    sc:carriedByVessel ex:v_vlcc ;
    sc:hasLoadPort ex:port_ras_tanura ;
    sc:hasDischargePort ex:port_rotterdam ;
    sc:hasLoadedQuantity ex:qty_loaded ;
    sc:hasLaycan ex:laycan1 .

ex:c1 a sc:SpotContract ;
    sc:hasCargo ex:cargo1 .

ex:nom1 a sc:VesselNomination ;
    sc:forCargo ex:cargo1 ;
    sc:nominatesVessel ex:v_vlcc ;
    sc:eventDate "2026-04-28"^^xsd:date .

ex:nor1 a sc:NoticeOfReadiness ;
    sc:forCargo ex:cargo1 ;
    sc:eventDate "2026-05-10"^^xsd:date .

ex:load1 a sc:LoadingEvent ;
    sc:forCargo ex:cargo1 ;
    sc:eventDate "2026-05-11"^^xsd:date .
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

    # Laycan inferred under OWL-Time hierarchy
    assert (SC.Laycan, RDFS.subClassOf, TIME.ProperInterval) in g
    assert (EX.laycan1, RDF.type, TIME.ProperInterval) in g
    assert (EX.laycan1, RDF.type, TIME.Interval) in g
    assert (EX.laycan1, RDF.type, TIME.TemporalEntity) in g

    # Exact AFRA classification based on deadweightTonnage
    expected_vessels: dict[URIRef, set[URIRef]] = {
        EX.v_afra: {SC.Aframax},
        EX.v_suez: {SC.Suezmax},
        EX.v_vlcc: {SC.VLCC},
        EX.v_below_afra: set(),
        EX.v_afra_min: {SC.Aframax},
        EX.v_afra_max: {SC.Aframax},
        EX.v_suez_min: {SC.Suezmax},
        EX.v_suez_max: {SC.Suezmax},
        EX.v_vlcc_min: {SC.VLCC},
    }
    for vessel, expected_classes in expected_vessels.items():
        actual_classes = set(g.objects(vessel, RDF.type)) & AFRA_CLASSES
        assert actual_classes == expected_classes, (
            f"Mismatch for {vessel}: got {actual_classes}, expected {expected_classes}"
        )
