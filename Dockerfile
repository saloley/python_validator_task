# Use official Python runtime as base image
FROM python:3.12-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY build/requirements.txt /app/build/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/build/requirements.txt

# Create necessary directories
RUN mkdir -p /app/src/files/raw \
             /app/src/files/source \
             /app/src/files/static \
             /app/src/files/raw/reports \
             /app/src/validation_service

# Copy project files
COPY src/ /app/src/
COPY .env /app/.env

# Set the default command
CMD ["python", "-m", "src.validation_service.run_valid_to_check"]
