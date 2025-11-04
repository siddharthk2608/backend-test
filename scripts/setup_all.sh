#!/bin/bash

echo "Setting up AI Tax Planning Application..."

# Create virtual environment
echo "Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies for all services
echo "Installing dependencies..."
pip install --upgrade pip

cd services/pdf-extraction-service
pip install -r requirements.txt
cd ../..

cd services/tax-planning-service
pip install -r requirements.txt
cd ../..

cd services/tax-data-service
pip install -r requirements.txt
cd ../..

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env files with your API keys"
echo "2. Run: ./scripts/start_services.sh"
