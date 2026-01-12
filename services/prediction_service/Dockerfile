FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Copy service code
COPY services/prediction_service/ ./services/prediction_service/

# Create directories
RUN mkdir -p models data logs

EXPOSE 8002

CMD ["python", "services/prediction_service/app.py"]
