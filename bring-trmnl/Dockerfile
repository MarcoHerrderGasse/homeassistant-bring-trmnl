FROM python:3.12-alpine

RUN apk add --no-cache bash

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x run.sh

CMD ["/app/run.sh"]
