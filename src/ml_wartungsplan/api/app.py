from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException

from ml_wartungsplan.api.schemas import (
    DeadlineRequest,
    FullRecommendationRequest,
    RecommendationResponse,
    StrategyRequest,
)
from ml_wartungsplan.services.email_renderer import EmailRenderer
from ml_wartungsplan.services.recommender import RecommendationService

load_dotenv()

app = FastAPI(
    title="ML Wartungsplan API",
    version="0.1.0",
    description=(
        "Strategy and realistic Eckende recommendations for SAP maintenance."
    ),
)


def verify_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    expected = os.getenv("MLW_API_KEY")
    if expected and expected != "change-me" and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key.")


@lru_cache(maxsize=1)
def service() -> RecommendationService:
    return RecommendationService()


@lru_cache(maxsize=1)
def renderer() -> EmailRenderer:
    return EmailRenderer()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/recommend/strategy",
    response_model=RecommendationResponse,
    dependencies=[Depends(verify_api_key)],
)
def recommend_strategy(
    request: StrategyRequest,
) -> RecommendationResponse:
    request_data = request.model_dump()
    recommendation = service().recommend_strategy(request_data)
    email_html = renderer().strategy_email(request_data, recommendation)
    return RecommendationResponse(
        recommendation=recommendation,
        email_html=email_html,
    )


@app.post(
    "/recommend/eckende",
    response_model=RecommendationResponse,
    dependencies=[Depends(verify_api_key)],
)
def recommend_eckende(
    request: DeadlineRequest,
) -> RecommendationResponse:
    request_data = request.model_dump(mode="json")
    recommendation = service().recommend_eckende(request_data)
    email_html = renderer().deadline_email(request_data, recommendation)
    return RecommendationResponse(
        recommendation=recommendation,
        email_html=email_html,
    )


@app.post(
    "/recommend/full",
    dependencies=[Depends(verify_api_key)],
)
def recommend_full(
    request: FullRecommendationRequest,
) -> dict[str, object]:
    strategy_request = request.strategy.model_dump()
    strategy_recommendation = service().recommend_strategy(
        strategy_request
    )

    output: dict[str, object] = {
        "strategy": strategy_recommendation,
        "strategy_email_html": renderer().strategy_email(
            strategy_request,
            strategy_recommendation,
        ),
    }

    if request.deadline is not None:
        deadline_request = request.deadline.model_dump(mode="json")
        deadline_recommendation = service().recommend_eckende(
            deadline_request
        )
        output["deadline"] = deadline_recommendation
        output["deadline_email_html"] = renderer().deadline_email(
            deadline_request,
            deadline_recommendation,
        )

    return output
