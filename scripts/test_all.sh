#!/bin/bash

echo "Testing all services..."

echo ""
echo "1. Testing PDF Extraction Service..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "2. Testing Tax Planning Service..."
curl -s http://localhost:8001/api/v1/planning/health | python3 -m json.tool

echo ""
echo "3. Testing Tax Data Service..."
# curl -s http://localhost:8002/health | python3 -m json.tool
curl -s http://localhost:8002/api/v1/health | python3 -m json.tool

echo ""
echo "All tests complete"
