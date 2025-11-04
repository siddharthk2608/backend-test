## Services

1. **PDF Extraction Service** (Port 8000)
   - Extracts data from tax return PDFs
   - Uses Claude AI for intelligent parsing

2. **Tax Planning Service** (Port 8001)
   - AI-powered tax analysis
   - Generates recommendations
   - Calculates tax scenarios

3. **Tax Data Service** (Port 8002)
   - Stores user tax data
   - Provides data access layer

## Quick Start

### Local Development
```bash
# 1. Setup
./scripts/setup_all.sh

# 2. Configure API keys
# Edit services/*/. env files

# 3. Start services
./scripts/start_services.sh

# 4. Test
./scripts/test_all.sh

# 5. Stop
./scripts/stop_services.sh
```

### Docker Deployment
```bash
# Build and start
docker-compose up -d

# Stop
docker-compose down
```

## API Endpoints

### PDF Extraction (8000)
- POST /process-tax-return
- GET /health

### Tax Planning (8001)
- POST /api/v1/planning/analyze
- GET /api/v1/planning/health

### Tax Data (8002)
- POST /api/v1/taxdata/users/{user_id}/data
- GET /api/v1/taxdata/users/{user_id}/data
- GET /health

## Development

Each service has its own README with detailed documentation.

## Testing
```bash
# Test all services
./scripts/test_all.sh

# Test individual service
curl http://localhost:8000/health
curl http://localhost:8001/api/v1/planning/health
curl http://localhost:8002/health
```
EOF

echo "✅ Root README created"