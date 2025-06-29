FROM python:3.10-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    libxml2-dev \
    libxmlsec1-openssl \
    libxmlsec1 \
    libxml2 \
    pkg-config \
    libssl-dev \
    libssl-dev \
    gcc

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip

# Force lxml and xmlsec to build from source against the correct system libraries
RUN pip install --no-binary=:all: lxml xmlsec

# Install the rest of your dependencies
RUN pip install -r requirements.txt

# collect static
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
