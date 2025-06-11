FROM python:3.10-slim

# Install system dependencies for pyheif (libheif + build tools)
RUN apt-get update && apt-get install -y \
    libheif-dev \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip setuptools

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose the port your app uses
EXPOSE 5000

# Run your Flask app
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000"]
