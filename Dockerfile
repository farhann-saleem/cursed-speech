# Cache-bust: v3
FROM runpod/base:0.6.2-cuda12.2.0

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/hf_cache

# Ensure python symlink exists
RUN ln -sf $(which python3) /usr/local/bin/python 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install torch+torchaudio with CUDA 12.4 first
RUN python3 -m pip install --no-cache-dir torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124

# Install chatterbox-tts deps manually (skip torch conflict)
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt && \
    python3 -m pip install --no-cache-dir --no-deps chatterbox-tts

# Pre-download model weights
RUN python3 -c "from chatterbox.tts import ChatterboxTTS; ChatterboxTTS.from_pretrained(device='cpu')" || true

COPY handler.py /app/handler.py

CMD ["python3", "-u", "/app/handler.py"]
