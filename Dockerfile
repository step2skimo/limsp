# Use official Python image
FROM python:3.11-slim

# Install required system libraries
RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    gcc \
    libxml2-dev \
    libxmlsec1-openssl

# Set workdir
WORKDIR /app

# Copy your code
COPY . /app

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run migrations automatically
# (optional, remove if you want to do it manually)
# RUN python manage.py migrate

# Collect static files (optional)
# RUN python manage.py collectstatic --noinput

# Start gunicorn
CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
