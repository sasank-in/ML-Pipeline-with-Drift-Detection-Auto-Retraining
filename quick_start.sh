#!/bin/bash

# Quick Start Script for ML Pipeline
# This script sets up and runs the entire ML pipeline

echo "=========================================="
echo "  ML Pipeline Quick Start"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs models

# Build and start services
echo ""
echo "🐳 Building and starting Docker containers..."
docker-compose up --build -d

# Wait for services to start
echo ""
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Check service health
echo ""
echo "🔍 Checking service health..."

services=(
    "http://localhost:8001/health:Ingestion API"
    "http://localhost:8002/health:Prediction Service"
)

for service in "${services[@]}"; do
    IFS=':' read -r url name <<< "$service"
    if curl -s "$url" > /dev/null; then
        echo "✅ $name is running"
    else
        echo "❌ $name is not responding"
    fi
done

echo ""
echo "=========================================="
echo "  Services Started Successfully!"
echo "=========================================="
echo ""
echo "📊 Dashboard: http://localhost:8050"
echo "🔌 Ingestion API: http://localhost:8001"
echo "🤖 Prediction Service: http://localhost:8002"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
echo ""
echo "🚀 Run example: python example_pipeline.py"
echo ""
