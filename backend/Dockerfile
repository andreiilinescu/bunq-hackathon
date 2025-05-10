# Base image
FROM python:3.13-slim

# Set work directory
WORKDIR /

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Flask’s default port
EXPOSE 5005

# Use Gunicorn for production
CMD ["python", "server.py"]
