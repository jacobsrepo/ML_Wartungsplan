from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class StrategyRequest(BaseModel):
    responsible_work_center: str
    technical_location: str
    task_description: str
    equipment_id: str | None = None
    equipment_text: str | None = None


class DeadlineRequest(BaseModel):
    order_number: str | None = None
    responsible_work_center: str
    technical_location: str
    task_description: str
    strategy: str
    planned_date: date

    cycle_days: float | None = Field(default=None, ge=0)
    call_date: date | None = None
    current_eckende: date | None = None
    task_list_group: str | None = None
    factory_calendar: str | None = None
    call_confirm: str | None = None
    opening_horizon_days: float | None = None
    opening_horizon_percent: float | None = None
    late_shift_percent: float | None = None
    late_tolerance_percent: float | None = None
    early_shift_percent: float | None = None
    early_tolerance_percent: float | None = None
    stretch_factor: float | None = None


class FullRecommendationRequest(BaseModel):
    strategy: StrategyRequest
    deadline: DeadlineRequest | None = None


class RecommendationResponse(BaseModel):
    recommendation: dict[str, Any]
    email_html: str | None = None
