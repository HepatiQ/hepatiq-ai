"""Write the v2 survival and landmark cohort artifacts.

Run:
    python -m hepatiq.data.build_cohorts

Inputs:  data/external/pbc.csv, data/external/pbcseq.csv (provenance verified)
Outputs: data/processed/v2_survival_cohort.csv
         data/processed/v2_landmark_cohort.csv
         data/processed/v2_cohort_manifest.json
"""

from __future__ import annotations

import json

from hepatiq.data.cohorts import (
    SURVIVAL_EVENT_COLUMN,
    build_landmark_cohort,
    build_survival_cohort,
    cohort_manifest,
)
from hepatiq.paths import V2_COHORT_MANIFEST, V2_LANDMARK_COHORT, V2_SURVIVAL_COHORT


def main() -> int:
    survival = build_survival_cohort()
    landmark = build_landmark_cohort()
    manifest = cohort_manifest()

    V2_SURVIVAL_COHORT.parent.mkdir(parents=True, exist_ok=True)
    survival.to_csv(V2_SURVIVAL_COHORT, index=False, lineterminator="\n")
    landmark.to_csv(V2_LANDMARK_COHORT, index=False, lineterminator="\n")
    V2_COHORT_MANIFEST.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Survival cohort: {len(survival)} patients, "
        f"{int(survival[SURVIVAL_EVENT_COLUMN].sum())} events -> {V2_SURVIVAL_COHORT}"
    )
    print(
        f"Landmark cohort: {len(landmark)} patients, "
        f"{int(landmark[SURVIVAL_EVENT_COLUMN].sum())} events -> {V2_LANDMARK_COHORT}"
    )
    print(f"Manifest -> {V2_COHORT_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
