# syntax=docker/dockerfile:1
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["uvicorn", "emperator.api:app", "--host", "0.0.0.0", "--port", "8000"]
