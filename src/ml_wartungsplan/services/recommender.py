from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml_wartungsplan.features.dates import (
    add_business_days,
    business_days_between,
    calendar_features,
    german_holiday_dates,
)
from ml_wartungsplan.features.text import (
    frequency_hint,
    hash_bucket,
    keyword_features,
    technical_location_area,
)
from ml_wartungsplan.models.deadline import FEATURE_COLUMNS as DEADLINE_FEATURE_COLUMNS
from ml_wartungsplan.models.deadline import predict_quantiles
from ml_wartungsplan.models.strategy import FEATURE_COLUMNS as STRATEGY_FEATURE_COLUMNS
from ml_wartungsplan.models.strategy import strategy_probabilities
from ml_wartungsplan.settings import (
    load_guardrails,
    load_settings,
    resolve_project_path,
)


class RecommendationService:
    def __init__(
        self,
        *,
        strategy_model_path: str | Path | None = None,
        deadline_model_path: str | Path | None = None,
    ) -> None:
        self.settings = load_settings()
        self.guardrails = load_guardrails()

        paths = self.settings["paths"]
        strategy_path = resolve_project_path(
            strategy_model_path or paths["strategy_model"]
        )
        deadline_path = resolve_project_path(
            deadline_model_path or paths["deadline_model"]
        )

        self.strategy_model = (
            joblib.load(strategy_path) if strategy_path.exists() else None
        )
        self.deadline_bundle = (
            joblib.load(deadline_path) if deadline_path.exists() else None
        )

    def recommend_strategy(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.strategy_model is None:
            raise FileNotFoundError(
                "Strategy model not found. Run scripts/02_train_strategy.py."
            )

        task_text = " | ".join(
            part
            for part in [
                str(request.get("task_description") or "").strip(),
                str(request.get("equipment_text") or "").strip(),
            ]
            if part
        ) or "UNKNOWN"

        item = pd.DataFrame(
            [
                {
                    "responsible_work_center": (
                        request.get("responsible_work_center") or "UNKNOWN"
                    ),
                    "technical_location_area": technical_location_area(
                        request.get("technical_location")
                    ),
                    "has_equipment": int(
                        bool(str(request.get("equipment_id") or "").strip())
                    ),
                    "task_description_text": task_text,
                    "frequency_hint": frequency_hint(task_text),
                }
            ]
        )
        recommendation = strategy_probabilities(
            self.strategy_model,
            item[STRATEGY_FEATURE_COLUMNS],
        ).iloc[0].to_dict()

        confidence = float(recommendation["prediction_confidence"])
        strategy_settings = self.settings["strategy_model"]
        if confidence >= strategy_settings["confidence_high"]:
            review_status = "high_confidence_recommendation"
        elif confidence >= strategy_settings["confidence_planner_review"]:
            review_status = "planner_confirmation_required"
        else:
            review_status = "manual_review_required"

        return {
            **recommendation,
            "review_status": review_status,
            "frequency_hint": item.iloc[0]["frequency_hint"],
            "technical_location_area": item.iloc[0][
                "technical_location_area"
            ],
        }

    def _deadline_feature_row(
        self,
        request: dict[str, Any],
    ) -> pd.DataFrame:
        planned_date = pd.Timestamp(request["planned_date"]).normalize()
        call_date_value = request.get("call_date")
        call_date = (
            pd.Timestamp(call_date_value).normalize()
            if call_date_value
            else pd.NaT
        )
        current_eckende_value = request.get("current_eckende")
        current_eckende = (
            pd.Timestamp(current_eckende_value).normalize()
            if current_eckende_value
            else pd.NaT
        )

        german_state = self.settings["project"]["german_state"]
        years = [planned_date.year, planned_date.year + 1]
        holiday_dates = german_holiday_dates(years, german_state)

        task_text = str(
            request.get("task_description") or "UNKNOWN"
        ).strip()
        row: dict[str, Any] = {
            "task_description_text": task_text,
            "responsible_work_center": request.get(
                "responsible_work_center",
                "UNKNOWN",
            ),
            "technical_location_area": technical_location_area(
                request.get("technical_location")
            ),
            "frequency_hint": frequency_hint(task_text),
            "strategy": request.get("strategy") or "UNKNOWN",
            "factory_calendar": request.get("factory_calendar") or "UNKNOWN",
            "call_confirm": request.get("call_confirm") or "UNKNOWN",
            "task_list_group_bucket": hash_bucket(
                request.get("task_list_group")
            ),
            "cycle_days": request.get("cycle_days"),
            "opening_horizon_days": request.get("opening_horizon_days"),
            "opening_horizon_percent": request.get(
                "opening_horizon_percent"
            ),
            "late_shift_percent": request.get("late_shift_percent"),
            "late_tolerance_percent": request.get(
                "late_tolerance_percent"
            ),
            "early_shift_percent": request.get("early_shift_percent"),
            "early_tolerance_percent": request.get(
                "early_tolerance_percent"
            ),
            "stretch_factor": request.get("stretch_factor"),
            "call_lead_workdays": (
                business_days_between(
                    call_date,
                    planned_date,
                    holiday_dates,
                )
                if pd.notna(call_date)
                else np.nan
            ),
            "current_eckende_extension_workdays": (
                max(
                    0,
                    business_days_between(
                        planned_date,
                        current_eckende,
                        holiday_dates,
                    ),
                )
                if pd.notna(current_eckende)
                else np.nan
            ),
        }
        row.update(calendar_features(planned_date))
        row.update(keyword_features(task_text))
        return pd.DataFrame([row])[DEADLINE_FEATURE_COLUMNS]

    def recommend_eckende(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.deadline_bundle is None:
            raise FileNotFoundError(
                "Deadline model not found. Run scripts/03_train_deadline.py."
            )

        features = self._deadline_feature_row(request)
        quantile_predictions = predict_quantiles(
            self.deadline_bundle,
            features,
        ).iloc[0]

        selected_quantile = float(
            self.deadline_bundle["selected_quantile"]
        )
        selected_key = f"q{int(round(selected_quantile * 100)):02d}"
        raw_extension = float(
            quantile_predictions[f"predicted_extension_{selected_key}"]
        )
        extension = max(0, int(math.ceil(raw_extension)))

        deadline_rules = self.guardrails["deadline"]
        reasons: list[str] = []
        capped = False

        absolute_max = int(
            deadline_rules["absolute_max_extension_workdays"]
        )
        if extension > absolute_max:
            extension = absolute_max
            capped = True
            reasons.append("absolute_maximum_applied")

        cycle_days = request.get("cycle_days")
        if cycle_days not in (None, ""):
            cycle_cap = max(
                0,
                int(
                    math.floor(
                        float(cycle_days)
                        * float(deadline_rules["maximum_cycle_fraction"])
                    )
                ),
            )
            if extension > cycle_cap:
                extension = cycle_cap
                capped = True
                reasons.append("cycle_fraction_cap_applied")

        extension = max(
            int(deadline_rules["minimum_extension_workdays"]),
            extension,
        )

        history_key = "||".join(
            [
                str(
                    request.get(
                        "responsible_work_center",
                        "UNKNOWN",
                    )
                ),
                technical_location_area(
                    request.get("technical_location")
                ),
                str(request.get("strategy") or "UNKNOWN"),
            ]
        )
        history_count = int(
            self.deadline_bundle["history_counts"].get(history_key, 0)
        )
        if history_count < int(
            deadline_rules["minimum_similar_history"]
        ):
            reasons.append("insufficient_similar_history")

        planned_date = pd.Timestamp(request["planned_date"]).normalize()
        german_state = self.settings["project"]["german_state"]
        holiday_dates = german_holiday_dates(
            [planned_date.year, planned_date.year + 1],
            german_state,
        )
        recommended_date = add_business_days(
            planned_date,
            extension,
            holiday_dates,
        )

        if reasons or (
            capped
            and deadline_rules.get("manual_review_if_capped", True)
        ):
            review_status = "manual_review_required"
        else:
            review_status = "planner_confirmation_required"

        quantile_output = {
            key.replace("predicted_extension_", ""): float(value)
            for key, value in quantile_predictions.to_dict().items()
        }

        return {
            "recommended_eckende": recommended_date.date().isoformat(),
            "recommended_extension_workdays": extension,
            "raw_selected_quantile_extension": raw_extension,
            "selected_service_level": selected_quantile,
            "quantile_extensions": quantile_output,
            "similar_history_count": history_count,
            "guardrail_applied": capped,
            "manual_review_reasons": reasons,
            "review_status": review_status,
        }
