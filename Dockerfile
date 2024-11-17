FROM python:3.12

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY server server
COPY static static

EXPOSE 8000
WORKDIR server
ENTRYPOINT gunicorn --bind 0.0.0.0:8000 wsgi:app
