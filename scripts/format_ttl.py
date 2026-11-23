#!/usr/bin/env python3
"""Format all Turtle (.ttl) files in ontology/ using rdflib."""

from pathlib import Path
from rdflib import Graph

ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "ontology"


def main() -> None:
    for path in sorted(ONTOLOGY_DIR.glob("*.ttl")):
        g = Graph().parse(path, format="turtle")
        g.serialize(destination=str(path), format="turtle")
        print(f"Formatted {path.relative_to(ONTOLOGY_DIR.parent)}")


if __name__ == "__main__":
    main()
