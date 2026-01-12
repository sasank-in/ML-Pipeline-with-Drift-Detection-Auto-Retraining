FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Copy service code
COPY services/ingestion_api/ ./services/ingestion_api/

# Create directories
RUN mkdir -p data logs

EXPOSE 8001

CMD ["python", "services/ingestion_api/app.py"]
