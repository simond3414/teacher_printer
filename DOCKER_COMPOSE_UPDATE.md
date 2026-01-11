# Updated Docker Compose Configuration for Teacher Printer

This document provides the updated `docker-compose.yml` configuration for your server to fix the RQ queue conflicts.

## Updated docker-compose.yml

Replace your current `docker-compose.yml` with this updated version:

```yaml
version: '3.8'

services:
  teacher-printer:
    image: simond3414/teacher-printer:latest
    ports:
      - "8507:8507"
    volumes:
      - /mnt/workbench/printer/printer_inputs:/app/printer_inputs
      - /mnt/workbench/printer/printer_outputs:/app/printer_outputs
      - /mnt/workbench/printer/printer_processes:/app/printer_processes
    working_dir: /app
    environment:
      - STREAMLIT_SERVER_PORT=8507
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - REDIS_URL=redis://shared-redis:6379
      - TP_QUEUE=teacher_printer
      - PYTHONPATH=/app
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    restart: unless-stopped
    networks:
      - redis_net

  rq-dashboard:
    image: cjlapao/rq-dashboard:latest
    ports:
      - "9181:9181"
    environment:
      - RQ_DASHBOARD_REDIS_URL=redis://shared-redis:6379
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
    restart: unless-stopped
    networks:
      - redis_net

  teacher-printer-worker:
    image: simond3414/teacher-printer:latest
    command: rq worker --url redis://shared-redis:6379 --path /app teacher_printer
    volumes:
      - /mnt/workbench/printer/printer_inputs:/app/printer_inputs
      - /mnt/workbench/printer/printer_outputs:/app/printer_outputs
      - /mnt/workbench/printer/printer_processes:/app/printer_processes
    working_dir: /app
    environment:
      - REDIS_URL=redis://shared-redis:6379
      - TP_QUEUE=teacher_printer
      - PYTHONPATH=/app
    deploy:
      resources:
        limits:
          memory: 1536M
          cpus: '1.0'
    restart: unless-stopped
    networks:
      - redis_net

networks:
  redis_net:
    external: true
```

## Key Changes

### 1. Environment Variables Updated

**teacher-printer service:**
- Changed: `REDIS_HOST` and `REDIS_PORT` → `REDIS_URL=redis://shared-redis:6379`
- Added: `TP_QUEUE=teacher_printer`

**teacher-printer-worker service:**
- Changed: `REDIS_HOST` and `REDIS_PORT` → `REDIS_URL=redis://shared-redis:6379`
- Added: `TP_QUEUE=teacher_printer`

### 2. Worker Command Updated

**Before:**
```bash
command: rq worker --url redis://shared-redis:6379 --path /app default
```

**After:**
```bash
command: rq worker --url redis://shared-redis:6379 --path /app teacher_printer
```

The worker now listens to the dedicated `teacher_printer` queue instead of `default`.

## Deployment Steps

1. **Stop the current deployment:**
   ```bash
   docker-compose down
   ```

2. **Pull the latest image** (after you rebuild and push with the updated code):
   ```bash
   docker pull simond3414/teacher-printer:latest
   ```

3. **Update your docker-compose.yml** with the configuration above

4. **Start the services:**
   ```bash
   docker-compose up -d
   ```

5. **Verify the worker is listening to the correct queue:**
   ```bash
   docker-compose logs teacher-printer-worker
   ```
   
   You should see a line like:
   ```
   Listening on teacher_printer...
   ```

## Verification

1. **Check the RQ Dashboard** at `http://your-server:9181`
   - You should see the `teacher_printer` queue listed
   - Jobs should appear there when you upload PDFs

2. **Monitor logs:**
   ```bash
   # Watch worker logs
   docker-compose logs -f teacher-printer-worker
   
   # Watch app logs
   docker-compose logs -f teacher-printer
   ```

3. **Test the application:**
   - Upload a PDF
   - Verify jobs appear in the `teacher_printer` queue (not `default`)
   - Check that jobs complete successfully

## Troubleshooting

### Jobs still going to 'default' queue
- Ensure you've rebuilt the Docker image with the updated code
- Check environment variables are set correctly: `docker-compose exec teacher-printer env | grep -E '(REDIS_URL|TP_QUEUE)'`

### Worker not processing jobs
- Verify worker is listening to `teacher_printer`: `docker-compose logs teacher-printer-worker | grep Listening`
- Check Redis connectivity: `docker-compose exec teacher-printer-worker redis-cli -h shared-redis ping`

### Import errors in worker
- Ensure `PYTHONPATH=/app` is set in worker environment
- Verify the image includes all updated code files

## Benefits of This Configuration

1. **Isolation**: Your teacher_printer jobs won't interfere with other applications using the same Redis instance
2. **Reliability**: Dedicated queue prevents cross-app import errors
3. **Monitoring**: RQ Dashboard can clearly show teacher_printer queue status
4. **Retry Logic**: Built-in retry mechanism (max 3 attempts) for failed jobs
5. **Job Tracking**: Unique job IDs with `tp:` prefix for easy identification
