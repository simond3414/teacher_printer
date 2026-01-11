# Redis Background Jobs Setup Guide

## Quick Start (Production - Docker Compose)

```bash
# Build and start all services
docker-compose up --build -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f teacher-printer-worker

# Stop all services
docker-compose down
```

## Local Development (Laptop)

### Start Redis locally
```bash
docker run -d --name redis-local -p 6379:6379 redis:7-alpine
```

### Install Python dependencies
```bash
pip install -r requirements.txt
```

### Run Streamlit locally
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
streamlit run app.py --server.port=8507
```

### Run Worker locally (in separate terminal)
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
rq worker --url redis://localhost:6379 default
```

## Architecture Overview

- **Web UI** (512MB, 0.5 CPU): Streamlit interface at http://localhost:8507
- **Redis** (256MB, 0.25 CPU): Message broker for job queue
- **Worker** (1.5GB, 1.0 CPU): Background processing container

## How It Works

1. User uploads PDF → Web UI creates job and submits to Redis queue
2. Worker picks up job → Converts PDF to images in background
3. User assigns page numbers → Web UI saves selections
4. User clicks Generate PDF → Web UI submits to Redis queue
5. Worker generates final PDF → User downloads when complete

## Monitoring Jobs

- Check sidebar in Streamlit UI for real-time job status
- View worker logs: `docker-compose logs -f teacher-printer-worker`
- Check Redis queue: `docker exec teacher-printer-redis redis-cli LLEN rq:queue:default`

## Troubleshooting

### Redis connection failed
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
docker exec teacher-printer-redis redis-cli ping
# Should return: PONG
```

### Worker not processing jobs
```bash
# Check worker logs
docker-compose logs teacher-printer-worker

# Restart worker
docker-compose restart teacher-printer-worker
```

### Clear all jobs from queue
```bash
docker exec teacher-printer-redis redis-cli FLUSHDB
```
