from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ml_wartungsplan.services.recommender import RecommendationService


REQUIRED_COLUMNS = [
    "responsible_work_center",
    "technical_location",
    "task_description",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample/strategy_requests.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/strategy/new_recommendations.csv"),
    )
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    missing = sorted(set(REQUIRED_COLUMNS).difference(data.columns))
    if missing:
        raise ValueError(f"Input CSV is missing columns: {missing}")

    service = RecommendationService()
    recommendations = [
        service.recommend_strategy(row.dropna().to_dict())
        for _, row in data.iterrows()
    ]
    output = pd.concat(
        [data.reset_index(drop=True), pd.DataFrame(recommendations)],
        axis=1,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(output):,} recommendations to {args.output}")


if __name__ == "__main__":
    main()
