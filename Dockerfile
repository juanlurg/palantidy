FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose Stremio Addon port
EXPOSE 7000

ENV PALANTIDY_HOST=0.0.0.0
ENV PALANTIDY_PORT=7000
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
