FROM python:3.12-slim

WORKDIR /app
COPY sidecar/market/requirements.txt /tmp/sidecar-req.txt
RUN pip install --no-cache-dir -r /tmp/sidecar-req.txt

COPY sidecar/market /app/sidecar/market

ENV FLASK_UPSTREAM=http://web:5000
EXPOSE 8001

CMD ["uvicorn", "sidecar.market.main:app", "--host", "0.0.0.0", "--port", "8001"]
