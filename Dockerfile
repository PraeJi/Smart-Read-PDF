FROM python:3.10-slim-bookworm

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "run_ngrok.py"]
