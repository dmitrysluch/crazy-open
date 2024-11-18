FROM python:3.12

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY server server

RUN mkdir -p ~/.postgresql && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" \
     --output-document ~/.postgresql/root.crt && \
    chmod 0600 ~/.postgresql/root.crt

WORKDIR /server
ENTRYPOINT gunicorn --worker-class gevent --bind 0.0.0.0:8000 wsgi:app
