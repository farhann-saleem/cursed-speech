FROM runpod/pytorch:2.4.0-py3.11-cuda12.1.1-devel-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download the base Chatterbox model (Optional but highly recommended)
# RUN git clone https://huggingface.co/your-repo/chatterbox-base /app/chatterbox-base

# Copy the serverless handler
COPY handler.py /app/handler.py

# Start the RunPod Serverless worker
CMD ["python", "-u", "/app/handler.py"]
