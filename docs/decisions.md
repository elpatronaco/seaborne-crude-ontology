# Iteration 1 Decisions

Locked on 2026-11-23:

1. **Transit risk, freight, and vessel nomination:** Contracts are classified automatically by Incoterm rules using OWL defined classes, and SPARQL queries resolve the corresponding buyer or seller.
2. **External ontologies:** OWL-Time is imported locally, QUDT, FIBO, and PMDCo Logistics use lightweight IRI alignments (IRIs pending verification), and GLEIF is deferred to PEC4.
3. **SHACL validation:** `pyshacl` is used for all validation rules.
4. **Laycan dates:** Laycans keep both an OWL-Time interval and plain start/end date properties.
