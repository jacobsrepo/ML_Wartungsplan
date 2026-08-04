from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ml_wartungsplan.settings import PROJECT_ROOT


class EmailRenderer:
    def __init__(self, template_dir: str | Path | None = None) -> None:
        directory = Path(template_dir or PROJECT_ROOT / "templates")
        self.environment = Environment(
            loader=FileSystemLoader(directory),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def strategy_email(
        self,
        request: dict[str, Any],
        recommendation: dict[str, Any],
    ) -> str:
        template = self.environment.get_template("strategy_email.html")
        return template.render(
            request=request,
            recommendation=recommendation,
        )

    def deadline_email(
        self,
        request: dict[str, Any],
        recommendation: dict[str, Any],
    ) -> str:
        template = self.environment.get_template("deadline_email.html")
        return template.render(
            request=request,
            recommendation=recommendation,
        )
