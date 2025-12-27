# Docker Usage for Teacher PDF Printer

## Architecture Overview

This application uses **three Docker containers** for optimal performance:

- **Redis** (256MB, 0.25 CPU): Message broker for background job queue
- **Web UI** (512MB, 0.5 CPU): Streamlit interface for user interaction
- **Worker** (1.5GB, 1.0 CPU): Background processor for heavy PDF operations

## Quick Start with Docker Compose (Recommended)

### Build and Start All Services
```bash
docker-compose up --build -d
```

### Access the Application
Open your browser to: `http://localhost:8507`

### Check Service Status
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f teacher-printer-worker
docker-compose logs -f teacher-printer-web
docker-compose logs -f redis
```

### Stop All Services
```bash
docker-compose down
```

### Restart Specific Service
```bash
docker-compose restart teacher-printer-worker
docker-compose restart teacher-printer-web
```

## Service Details

### Redis (teacher-printer-redis)
- **Port**: 6379
- **Memory**: 256MB limit
- **Purpose**: Job queue message broker
- **Health Check**: Automatically validates Redis is responding

### Web UI (teacher-printer-web)
- **Port**: 8507
- **Memory**: 512MB limit (lightweight, stays responsive)
- **Purpose**: Streamlit interface for job submission and monitoring
- **Depends on**: Redis must be healthy before starting

### Worker (teacher-printer-worker)
- **Memory**: 1.5GB limit (handles heavy processing)
- **Purpose**: Background PDF conversion and generation
- **Command**: `rq worker --url redis://redis:6379 default`
- **Depends on**: Redis must be healthy before starting

## Directory Bindings

The following directories are mounted as volumes to persist data across all containers:

- **printer_inputs/**: Uploaded PDF files
- **printer_outputs/**: Generated output PDFs
- **printer_processes/**: Active job data and selections

All data persists on your host machine even when containers are stopped or removed.

## Environment Variables

### Web UI & Worker
- `REDIS_HOST=redis` (service name in Docker network)
- `REDIS_PORT=6379`

### Web UI Only
- `STREAMLIT_SERVER_PORT=8507`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`

## How Background Processing Works

1. User uploads PDF via Web UI
2. Web UI submits job to Redis queue
3. Worker picks up job from Redis
4. Worker processes PDF in background (user can close browser)
5. User returns later and clicks "Refresh Job Status" to check progress
6. User downloads completed PDF

## Monitoring

### Check Job Queue Status
```bash
# Number of jobs in queue
docker exec teacher-printer-redis redis-cli LLEN rq:queue:default

# See all Redis keys
docker exec teacher-printer-redis redis-cli KEYS '*'
```

### Test Redis Connection
```bash
docker exec teacher-printer-redis redis-cli ping
# Should return: PONG
```

### Monitor Worker Activity
```bash
docker-compose logs -f teacher-printer-worker
# Watch for "WORKER:" log messages showing job processing
```

## Troubleshooting

### Services won't start
```bash
# Check all service status
docker-compose ps

# Check specific service logs
docker-compose logs teacher-printer-web
docker-compose logs teacher-printer-worker
docker-compose logs redis
```

### Redis connection failed
```bash
# Verify Redis is running and healthy
docker ps | grep redis

# Test Redis connection
docker exec teacher-printer-redis redis-cli ping
```

### Worker not processing jobs
```bash
# Check worker logs for errors
docker-compose logs teacher-printer-worker

# Restart worker
docker-compose restart teacher-printer-worker
```

### Port 8507 or 6379 already in use
```bash
# Check what's using the ports
lsof -i :8507
lsof -i :6379

# Stop conflicting services or change ports in docker-compose.yml
```

### Clear stuck jobs from queue
```bash
# Clear all Redis data (CAUTION: deletes all queued jobs)
docker exec teacher-printer-redis redis-cli FLUSHDB
```

### Permission issues with volumes
```bash
# Ensure directories exist and have correct permissions
mkdir -p printer_inputs printer_outputs printer_processes
chmod 755 printer_inputs printer_outputs printer_processes
```

### Rebuild after code changes
```bash
docker-compose down
docker-compose up --build -d
```

## Resource Management

The docker-compose.yml includes resource limits to prevent system overload:

- **Redis**: 256MB memory, 0.25 CPU
- **Web UI**: 512MB memory, 0.5 CPU
- **Worker**: 1.5GB memory, 1.0 CPU

These limits ensure the UI stays responsive while controlling processing load. Adjust in docker-compose.yml if needed for your workload.

## Production Deployment

For deployment on a server:

1. Pull updated code: `git pull`
2. Stop existing services: `docker-compose down`
3. Build and start: `docker-compose up -d --build`
4. Verify all services running: `docker-compose ps`
5. Access at: `http://server-ip:8507`

All services will automatically restart if they crash (configured with `restart: unless-stopped`).
