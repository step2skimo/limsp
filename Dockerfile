# Use modern Bookworm to get modern libxml2/libxmlsec1
FROM python:3.10-bookworm

RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    libxml2-dev \
    libxmlsec1-openssl \
    pkg-config \
    gcc

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
