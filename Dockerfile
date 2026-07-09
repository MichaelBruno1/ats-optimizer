FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    shared-mime-info \
    libffi-dev \
    libcairo2 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV RUNNING_IN_DOCKER=true

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app/ ./app/
# Copy frontend if it exists (built by the frontend agent)
COPY frontend/ ./static/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
