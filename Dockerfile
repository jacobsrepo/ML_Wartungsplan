FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY templates ./templates
COPY models ./models

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "ml_wartungsplan.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
