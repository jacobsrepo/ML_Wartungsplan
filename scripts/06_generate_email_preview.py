from __future__ import annotations

from pathlib import Path

from ml_wartungsplan.services.email_renderer import EmailRenderer
from ml_wartungsplan.services.recommender import RecommendationService


def main() -> None:
    strategy_request = {
        "responsible_work_center": "EH_STPM",
        "technical_location": "8160-330",
        "task_description": "wöchentlicher TPM Wartungsplan HFM6M3",
        "equipment_id": "HFM6M3",
        "equipment_text": "HFM6 Montageanlage",
    }

    deadline_request = {
        "order_number": "DEMO-001",
        "responsible_work_center": "EH_STPM",
        "technical_location": "8160-330",
        "task_description": "wöchentlicher TPM Wartungsplan HFM6M3",
        "strategy": "8160_W",
        "planned_date": "2026-09-10",
        "call_date": "2026-08-20",
        "cycle_days": 7,
        "opening_horizon_days": 14,
        "factory_calendar": "TH",
        "call_confirm": "X",
    }

    service = RecommendationService()
    renderer = EmailRenderer()

    strategy_recommendation = service.recommend_strategy(
        strategy_request
    )
    strategy_html = renderer.strategy_email(
        strategy_request,
        strategy_recommendation,
    )

    output_dir = Path("reports/email_previews")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "strategy_email.html").write_text(
        strategy_html,
        encoding="utf-8",
    )
    print("Created:", output_dir / "strategy_email.html")

    try:
        deadline_recommendation = service.recommend_eckende(
            deadline_request
        )
    except FileNotFoundError:
        print(
            "Deadline model not trained yet; skipping deadline preview."
        )
        return

    deadline_html = renderer.deadline_email(
        deadline_request,
        deadline_recommendation,
    )
    (output_dir / "deadline_email.html").write_text(
        deadline_html,
        encoding="utf-8",
    )
    print("Created:", output_dir / "deadline_email.html")


if __name__ == "__main__":
    main()
