FROM python:3.10.5-bullseye
RUN mkdir -p /python/tradebot
WORKDIR /python/tradebot
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["python"]
