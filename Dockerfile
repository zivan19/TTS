# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . .

RUN pip install --upgrade pip \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi \
    && if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi \
    && if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install .; fi

CMD ["bash"]
