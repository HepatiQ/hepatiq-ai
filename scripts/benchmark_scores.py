"""Benchmark published PBC/liver scores against the deployed v1 model.

Usage: python scripts/benchmark_scores.py
Writes docs/SCORE_BENCHMARK.md and docs/score_benchmark.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hepatiq.data import load_pbc, load_udca1  # noqa: E402
from hepatiq.risk.benchmark import (  # noqa: E402
    benchmark_derivation_validation_split,
    benchmark_pbc,
    benchmark_udca_stored_score,
    mayo_risk_distribution,
    to_markdown,
)


def main() -> int:
    pbc = load_pbc()
    udca1 = load_udca1()

    pbc_rows = benchmark_pbc(pbc)
    split = benchmark_derivation_validation_split(pbc)
    udca_row = benchmark_udca_stored_score(udca1)
    stored = udca1["riskscore"].dropna()
    udca_row["implementation_check"] = {
        "computed_pbc": mayo_risk_distribution(pbc),
        "stored_udca": {
            "n": int(stored.size),
            "mean": float(stored.mean()),
            "median": float(stored.median()),
            "sd": float(stored.std()),
        },
    }

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "SCORE_BENCHMARK.md").write_text(to_markdown(pbc_rows, udca_row, split), encoding="utf-8")
    (docs / "score_benchmark.json").write_text(
        json.dumps({"pbc": pbc_rows, "holdout": split, "udca1": udca_row}, indent=2),
        encoding="utf-8",
    )

    for row in pbc_rows:
        print(
            f"{row['score']:<34} AUC={row['auc_5y']:.3f} "
            f"C={row['c_index']:.3f} n5y={row['n_5y']}"
        )
    for row in split["scores"]:
        print(
            f"held-out 106: {row['score']:<44} AUC={row['auc_5y']:.3f} "
            f"C={row['c_index']:.3f} n5y={row['n_5y']}"
        )
    print(
        f"{udca_row['score']:<34} AUC={udca_row['auc_5y']:.3f} "
        f"C={udca_row['c_index']:.3f} n={udca_row['n_survival']}"
    )
    print("wrote docs/SCORE_BENCHMARK.md and docs/score_benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
