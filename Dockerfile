# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/project

# Set work directory at the repository root so manage.py and the project
# package are both importable by Django and Celery.
WORKDIR /app

# Install system dependencies needed for compiling python packages like psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY project/requirements.txt /app/project/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/project/requirements.txt

# Copy project files
COPY . /app/

# Expose Django port
EXPOSE 8000
