FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Baku \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Baku /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /app/data
VOLUME ["/app/data"]

CMD ["python", "-m", "reminder_bot"]
