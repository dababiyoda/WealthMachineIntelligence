FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy poetry config and lock file
COPY pyproject.toml .
RUN pip install --no-cache-dir poetry==1.7.0
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-dev

# Copy application source
COPY src ./src

# Copy scripts (if any)
COPY .pre-commit-config.yaml .pre-commit-config.yaml

EXPOSE 8000

CMD ["python", "-m", "src.api.main"]
