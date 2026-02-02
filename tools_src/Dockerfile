FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    qemu-utils \
    libtsk-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs configs triage

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "src.main", "--help"]



