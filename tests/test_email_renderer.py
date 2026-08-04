from ml_wartungsplan.services.email_renderer import EmailRenderer


def test_strategy_email_rendering() -> None:
    renderer = EmailRenderer()
    html = renderer.strategy_email(
        {
            "responsible_work_center": "EH_STPM",
            "technical_location": "8160-330",
            "task_description": "Weekly TPM",
        },
        {
            "predicted_strategy": "8160_W",
            "prediction_confidence": 0.91,
            "top_2_strategy": "UBK_W1",
            "top_2_probability": 0.07,
            "frequency_hint": "week",
            "review_status": "planner_confirmation_required",
        },
    )
    assert "8160_W" in html
    assert "91.0%" in html
