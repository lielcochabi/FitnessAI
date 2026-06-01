FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000
# Render (and other PaaS) inject $PORT; locally it defaults to 8000 so Docker
# Compose and Kubernetes behave exactly as before.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

