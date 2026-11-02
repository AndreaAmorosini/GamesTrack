FROM python:3.12

ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./ /code/app

# Il worker è un processo ARQ, non un server FastAPI
CMD ["arq", "app.worker_sync.WorkerSettings", "--watch", "app"]
