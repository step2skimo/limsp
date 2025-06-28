# Use Python 3.10
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    libxml2-dev \
    libxmlsec1-openssl \
    pkg-config \
    gcc

# Set working directory
WORKDIR /app

# Copy your project code
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# (optional) collect static files
# RUN python manage.py collectstatic --noinput

# Start gunicorn
CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
