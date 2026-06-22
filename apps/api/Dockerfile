FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /workspace

COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/api/app apps/api/app

WORKDIR /workspace/apps/api

RUN python -m pip install --upgrade pip \
    && python -m pip install -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
