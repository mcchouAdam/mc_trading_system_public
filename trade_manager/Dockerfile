FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY trade_manager/ ./trade_manager/
COPY backtest_engine/ ./backtest_engine/
COPY machine_learning/ ./machine_learning/

ENV PYTHONPATH=/app

CMD ["python", "-u", "trade_manager/order_executor.py"]
