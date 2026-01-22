FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data required by g2p-en
RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('cmudict')"

# Copy application code
COPY app/ ./app/

# Create exercises directory and copy example file
RUN mkdir -p /app/exercises
COPY --chmod=644 examples/pronunciation_exercises_example.xlsx /app/exercises/

# Create non-root user and set up directories
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/nltk_data && \
    cp -r /root/nltk_data/* /home/appuser/nltk_data/ && \
    chown -R appuser:appuser /app /home/appuser/nltk_data

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NLTK_DATA=/home/appuser/nltk_data

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the service
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
