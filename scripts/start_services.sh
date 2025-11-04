#!/bin/bash

echo "Starting all services..."

# Activate venv
source venv/bin/activate

# Start services in background
echo "Starting PDF Extraction Service (Port 8000)..."
cd services/pdf-extraction-service
python main.py > ../../logs/pdf-extraction.log 2>&1 &
PDF_PID=$!
cd ../..

sleep 2

echo "Starting Tax Planning Service (Port 8001)..."
cd services/tax-planning-service
python main.py > ../../logs/tax-planning.log 2>&1 &
PLANNING_PID=$!
cd ../..

sleep 2

echo "Starting Tax Data Service (Port 8002)..."
cd services/tax-data-service
python main.py > ../../logs/tax-data.log 2>&1 &
DATA_PID=$!
cd ../..

echo ""
echo "All services started!"
echo ""
echo "Service Status:"
echo "- PDF Extraction: http://localhost:8000 (PID: $PDF_PID)"
echo "- Tax Planning:   http://localhost:8001 (PID: $PLANNING_PID)"
echo "- Tax Data:       http://localhost:8002 (PID: $DATA_PID)"
echo ""
echo "Check logs in ./logs/"
echo "Stop services: ./scripts/stop_services.sh"
