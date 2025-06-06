FROM python:3.11-slim

# Install system dependencies for pyheif (libheif + build tools)
RUN apt-get update && apt-get install -y \
    libheif-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose the port your app uses
EXPOSE 5000

# Run your Flask app
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000"]
