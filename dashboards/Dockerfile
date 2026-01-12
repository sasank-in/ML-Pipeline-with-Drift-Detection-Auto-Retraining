FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Copy dashboard code
COPY dashboards/ ./dashboards/

# Create directories
RUN mkdir -p data logs

EXPOSE 8050

CMD ["python", "dashboards/monitoring_app.py"]
