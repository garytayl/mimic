# Base image
FROM python:3.11-slim

# Install system dependencies (FFmpeg, PostgreSQL dev libraries, and build tools)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    build-essential \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if needed for HTTP or other services)
EXPOSE 5000

# Run the bot
CMD ["python", "panshemlumus.py"]
