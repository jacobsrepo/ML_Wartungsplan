from __future__ import annotations

import importlib
import sys
from pathlib import Path

from ml_wartungsplan.settings import load_settings, resolve_project_path

REQUIRED_IMPORTS = [
    "fastapi",
    "holidays",
    "jinja2",
    "joblib",
    "matplotlib",
    "numpy",
    "openpyxl",
    "pandas",
    "sklearn",
    "uvicorn",
    "yaml",
]


def main() -> None:
    print("Python:", sys.version)
    failed: list[str] = []

    for module_name in REQUIRED_IMPORTS:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "installed")
            print(f"[OK] {module_name}: {version}")
        except ImportError as exc:
            failed.append(module_name)
            print(f"[MISSING] {module_name}: {exc}")

    settings = load_settings()
    raw_excel = resolve_project_path(settings["paths"]["raw_excel"])
    print("\nRaw SAP workbook:")
    print(raw_excel.resolve())
    print("Present:", raw_excel.exists())

    if failed:
        raise SystemExit(
            "\nInstall missing packages with: uv sync --extra dev"
        )

    if not raw_excel.exists():
        raise SystemExit(
            "\nCopy SAP_notintime_.xlsx into data/raw/ before building data."
        )

    print("\nEnvironment is ready.")


if __name__ == "__main__":
    main()
