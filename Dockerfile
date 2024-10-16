FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ethereum_ingestion.py .
COPY .env .

CMD ["python", "ethereum_ingestion.py"]