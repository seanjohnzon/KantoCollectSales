FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set working directory to backend
WORKDIR /app/KantoCollect/backend

# Expose port
EXPOSE 8000

# Railway sets PORT env var
ENV PORT=8000

# Start command - use shell form to expand $PORT
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
