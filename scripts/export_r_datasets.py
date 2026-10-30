"""Export the canonical PBC datasets from the CRAN `survival` package to CSV.

Why this exists
---------------
The longitudinal (`pbcseq`) and UDCA-trial (`udca`) cohorts are only shipped as
R binary artifacts inside CRAN's `survival` package. This project needs them as
plain CSV so the Python data layer can load and validate them reproducibly
without an R installation.

What it does
------------
1. Resolves the current `survival` version from CRAN's PACKAGES index.
2. Downloads the source tarball and reads only `data/*.rda` members.
3. Converts the wanted data.frame objects with `rdata` and writes one CSV each.
4. Records source URL, package version, row/column counts, and SHA-256 hashes in
   `data/external/PROVENANCE.json` so the CSVs are auditable.

Notes
-----
* `pbcseq` is bundled inside `data/pbc.rda` alongside `pbc`; there is no
  standalone `pbcseq.rda` in the source tarball. Both are exported here.
* `udca.rda` holds three objects: `udca` (event dates), `udca1` (one row per
  patient, survival-ready) and `udca2` (multiple endpoints per patient).

Run
---
    python scripts/export_r_datasets.py

The `rdata` package is a one-off export dependency and is intentionally NOT in
requirements.txt (runtime/CI never need it). Install it with:

    pip install rdata
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import rdata
    import rdata.conversion as rconversion
    from rdata.parser import RObjectType
except ImportError:  # pragma: no cover - tooling-only dependency
    sys.exit("This exporter needs the 'rdata' package: pip install rdata")

CRAN_BASE = "https://cran.r-project.org/src/contrib"
PACKAGES_URL = f"{CRAN_BASE}/PACKAGES.gz"

# Objects we export, in the order they should appear in the provenance file.
WANTED_OBJECTS = ("pbc", "pbcseq", "udca", "udca1", "udca2")

# Objects the downstream pipeline cannot function without.
REQUIRED_OBJECTS = ("pbc", "pbcseq", "udca")

# `rdata` has no Date constructor, so R `Date` columns arrive as raw numeric
# days since 1970-01-01. These are the date-typed columns in `survival::udca`.
UDCA_DATE_COLUMNS = (
    "entry.dt",
    "last.dt",
    "death.dt",
    "tx.dt",
    "hprogress.dt",
    "varices.dt",
    "ascites.dt",
    "enceph.dt",
    "double.dt",
    "worsen.dt",
)


def _get(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def resolve_survival_version() -> str:
    raw = gzip.decompress(_get(PACKAGES_URL)).decode("utf-8", errors="replace")
    for block in raw.split("\n\n"):
        if block.startswith("Package: survival\n"):
            for line in block.splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
    raise RuntimeError("Could not resolve the survival package version from CRAN")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _convert_r_dates(dataset: pd.DataFrame) -> pd.DataFrame:
    """Convert R `Date` columns (days since 1970-01-01) to ISO date strings."""
    dataset = dataset.copy()
    for column in UDCA_DATE_COLUMNS:
        if column not in dataset.columns:
            continue
        dates = pd.to_datetime(dataset[column], unit="D", origin="1970-01-01", errors="coerce")
        dataset[column] = dates.dt.strftime("%Y-%m-%d")
    return dataset


def _iter_top_level(r_object):
    """Yield (name, value_object) for each top-level object in an .rda file."""
    node = r_object
    while node is not None:
        if node.info.type is RObjectType.NILVALUE:
            return
        if node.info.type is not RObjectType.LIST:
            return
        name = rconversion.convert(node.tag) if node.tag is not None else None
        car, cdr = node.value
        yield name, car
        node = cdr


def export(out_dir: Path) -> dict:
    version = resolve_survival_version()
    tarball_url = f"{CRAN_BASE}/survival_{version}.tar.gz"
    print(f"survival {version} <- {tarball_url}")
    tarball = _get(tarball_url, timeout=180)

    out_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tarball_path = tmp_path / "survival.tar.gz"
        tarball_path.write_bytes(tarball)

        with tarfile.open(tarball_path, "r:gz") as archive:
            members = [
                member
                for member in archive.getmembers()
                if member.name.startswith("survival/data/")
                and member.name.endswith((".rda", ".RData"))
            ]
            if not members:
                raise RuntimeError("No data/*.rda members found in the survival tarball")
            archive.extractall(tmp_path, members=members)

        for member in members:
            parsed = rdata.parser.parse_file(tmp_path / member.name)
            for name, value in _iter_top_level(parsed.object):
                if name not in WANTED_OBJECTS:
                    continue
                try:
                    dataset = rconversion.convert(value)
                except Exception as error:  # noqa: BLE001 - report and continue
                    print(f"  skip {name}: conversion failed ({error})")
                    continue
                if not isinstance(dataset, pd.DataFrame):
                    continue
                if name.startswith("udca"):
                    dataset = _convert_r_dates(dataset)
                csv_path = out_dir / f"{name}.csv"
                dataset.to_csv(csv_path, index=False)
                records[name] = {
                    "object": name,
                    "file": csv_path.name,
                    "source_member": member.name,
                    "rows": int(dataset.shape[0]),
                    "columns": [str(column) for column in dataset.columns],
                    "sha256": _sha256(csv_path),
                }
                print(f"  wrote {csv_path.name}: {dataset.shape[0]} rows x {dataset.shape[1]} cols")

    missing = [name for name in REQUIRED_OBJECTS if name not in records]
    if missing:
        raise RuntimeError(f"Expected datasets were not exported: {missing}")

    provenance = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package": "survival",
        "package_version": version,
        "source_tarball": tarball_url,
        "tarball_sha256": hashlib.sha256(tarball).hexdigest(),
        "license": "LGPL (>= 2); datasets are redistributed from published sources",
        "notes": [
            "pbcseq is bundled inside survival/data/pbc.rda together with pbc.",
            "udca.rda contains udca (event dates), udca1 (survival-ready) and udca2 (multiple endpoints).",
            "R Date columns in udca were converted from days-since-1970-01-01 to ISO YYYY-MM-DD strings.",
        ],
        "datasets": {name: records[name] for name in WANTED_OBJECTS if name in records},
    }
    provenance_path = out_dir / "PROVENANCE.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {provenance_path}")
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser(description="Export survival::pbc/pbcseq/udca to CSV")
    parser.add_argument("--out-dir", type=Path, default=Path("data/external"))
    args = parser.parse_args()
    export(args.out_dir)


if __name__ == "__main__":
    main()
