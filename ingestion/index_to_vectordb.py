"""Compatibility entrypoint for building the local retrieval index.

The project currently uses a lightweight Minsearch pickle index. This module
keeps the README command stable while delegating to the implemented builder.
"""
from __future__ import annotations

from src.retrieval.build_index import main


if __name__ == "__main__":
    main()
