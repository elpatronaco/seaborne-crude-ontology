#!/usr/bin/env python3
"""Format all Turtle (.ttl) files in ontology/ using rdflib."""

from pathlib import Path
from rdflib import Graph

ONTOLOGY_DIR = Path(__file__).resolve().parent.parent / "ontology"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> None:
    for directory in [ONTOLOGY_DIR, DATA_DIR]:
        for path in sorted(directory.glob("*.ttl")):
            g = Graph().parse(path, format="turtle")
            g.serialize(destination=str(path), format="turtle")
            print(f"Formatted {path.relative_to(directory.parent)}")


if __name__ == "__main__":
    main()
