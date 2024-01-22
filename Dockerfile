FROM python:3.10-alpine3.19
LABEL authors="yank"

EXPOSE 9090

WORKDIR /app

COPY ./server.py .

CMD python server.py