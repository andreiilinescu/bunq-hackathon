# Base image
FROM python:3.13-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose Flask’s default port
EXPOSE 5000

# Use Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
