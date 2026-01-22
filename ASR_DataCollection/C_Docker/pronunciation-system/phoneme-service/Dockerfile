FROM python:3.11-slim

# Install system dependencies
# espeak-ng for phonemizer (text-to-IPA conversion)
# ffmpeg/libsndfile for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (no PyAV needed - using wav2vec2 directly)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir phonemizer && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data for g2p-en
RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('cmudict')"

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/models && \
    mkdir -p /home/appuser/nltk_data && \
    cp -r /root/nltk_data/* /home/appuser/nltk_data/ && \
    chown -R appuser:appuser /app /home/appuser/nltk_data

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/models \
    TORCH_HOME=/app/models/torch \
    NLTK_DATA=/home/appuser/nltk_data

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start the service
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
