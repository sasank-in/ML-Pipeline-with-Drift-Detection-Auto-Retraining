FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules, ML modules, and registry
COPY shared/ ./shared/
COPY ml/ ./ml/
COPY registry/ ./registry/

# Copy service code
COPY services/retraining_worker/ ./services/retraining_worker/

# Create directories
RUN mkdir -p models data logs

CMD ["python", "services/retraining_worker/worker.py"]
