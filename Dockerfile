FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set working directory to backend
WORKDIR /app/KantoCollect/backend

# Start command - Railway sets PORT env var dynamically
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
