"""Canonical PBC data access for HepatiQ v2.

Use these loaders instead of reading ``data/external/*.csv`` directly. They
validate the column contract, check pinned SHA-256 hashes, and raise
``DataIntegrityError`` when a file has drifted from the canonical export.
"""

from hepatiq.data.build_tables import (
    STATUS_LABELS,
    TRT_LABELS,
    dataset_summary,
    load_all,
    load_pbc,
    load_pbcseq,
    load_udca,
    load_udca1,
    load_udca2,
)
from hepatiq.data.provenance import DataIntegrityError, load_provenance, verify_datasets

__all__ = [
    "STATUS_LABELS",
    "TRT_LABELS",
    "DataIntegrityError",
    "dataset_summary",
    "load_all",
    "load_pbc",
    "load_pbcseq",
    "load_provenance",
    "load_udca",
    "load_udca1",
    "load_udca2",
    "verify_datasets",
]
