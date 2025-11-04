#!/bin/bash

echo "Stopping all services..."

# Kill services by port
kill $(lsof -t -i:8000) 2>/dev/null || echo "No service on port 8000"
kill $(lsof -t -i:8001) 2>/dev/null || echo "No service on port 8001"
kill $(lsof -t -i:8002) 2>/dev/null || echo "No service on port 8002"

echo "All services stopped"
