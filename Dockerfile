FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get -y install curl libmagic1 libmagic-dev gnupg software-properties-common apt-transport-https sqlite3

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN echo "deb [arch=amd64] https://packages.microsoft.com/debian/$(lsb_release -rs)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/microsoft.list

RUN apt-get update && ACCEPT_EULA=Y apt-get -y install unixodbc unixodbc-dev libpq-dev gcc msodbcsql17

RUN mkdir -p /app

COPY requirements.txt /app

COPY .env .
COPY ./gunicorn_conf.py /app

COPY ./app /app

RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt

ENV PORT=5001
EXPOSE 5001

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]