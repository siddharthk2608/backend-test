# FROM python:3.11-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# EXPOSE 8002
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]


FROM python:3.11-slim

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
# COPY services/tax-data-service/requirements.txt /app/requirements.txt
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# Copy only the tax-planning-service code and shared package
# COPY services/tax-data-service /app
# COPY services/shared /app/shared
COPY . /app

# Make /app importable
ENV PYTHONPATH=/app:/app/shared
ENV PYTHONUNBUFFERED=1

# Expose service port
EXPOSE 8002

# Run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
