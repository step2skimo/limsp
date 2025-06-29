FROM python:3.10-bookworm

RUN apt-get update && apt-get install -y \
    libxmlsec1-dev \
    libxml2-dev \
    libxmlsec1-openssl \
    pkg-config \
    libssl-dev \
    gcc

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip

# Force lxml and xmlsec to build from source *using system libraries*
RUN pip install --no-binary=:all: lxml xmlsec

# Then install the rest of the requirements
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
