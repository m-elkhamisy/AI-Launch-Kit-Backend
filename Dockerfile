FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system launchkit \
    && adduser --system --ingroup launchkit launchkit

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir --no-build-isolation .

RUN mkdir -p /app/local_data && chown -R launchkit:launchkit /app/local_data

EXPOSE 8000

USER launchkit

CMD ["uvicorn", "launchkit.main:app", "--host", "0.0.0.0", "--port", "8000"]
