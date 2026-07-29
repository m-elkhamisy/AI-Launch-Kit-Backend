FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system launchkit && adduser --system --ingroup launchkit launchkit

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --no-cache-dir .

RUN mkdir -p /app/local_data && chown -R launchkit:launchkit /app/local_data

EXPOSE 8000

USER launchkit

CMD ["uvicorn", "launchkit.main:app", "--host", "0.0.0.0", "--port", "8000"]