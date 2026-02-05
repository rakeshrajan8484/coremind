# Base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies (if needed, e.g. for building wheels)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the application in editable mode so imports work correctly
# or simply ensure pythonpath includes /app
RUN pip install -e .

# Expose port (default for Railway is usually 8000 or defined by $PORT)
EXPOSE 8000

# Command to run the application
# We use shell form to allow variable expansion for $PORT
CMD uvicorn coremind.server.api:app --host 0.0.0.0 --port ${PORT:-8000}
