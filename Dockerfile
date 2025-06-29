FROM python:3.10-slim

# install system dependencies
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    pkg-config \
    gcc \
    libxml2-utils \
    libxml2

# set workdir
WORKDIR /app

# copy code
COPY . /app

# upgrade pip
RUN pip install --upgrade pip

# reinstall lxml and xmlsec in sync with system libraries
RUN pip install --no-binary=:all: lxml xmlsec

# install other requirements
RUN pip install -r requirements.txt

# expose port
EXPOSE 8000

# start
CMD ["gunicorn", "lims_project.wsgi:application", "--bind", "0.0.0.0:8000"]
