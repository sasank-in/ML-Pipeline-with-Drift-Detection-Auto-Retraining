FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and ML modules
COPY shared/ ./shared/
COPY ml/ ./ml/

# Copy service code
COPY services/drift_monitor/ ./services/drift_monitor/

# Create directories
RUN mkdir -p data logs

CMD ["python", "services/drift_monitor/monitor.py"]
