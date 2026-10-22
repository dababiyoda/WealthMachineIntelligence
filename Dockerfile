# Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Disable pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY contracts ./contracts
COPY main.py ./main.py

# Expose API port
EXPOSE 5000

# Default command
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "5000"]
