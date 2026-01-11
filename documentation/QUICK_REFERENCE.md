# Quick Reference: RQ Queue Configuration

## Docker Compose Update (Server)

### Update these services in your docker-compose.yml:

**teacher-printer:**
```yaml
environment:
  - REDIS_URL=redis://shared-redis:6379  # Add this
  - TP_QUEUE=teacher_printer             # Add this
```

**teacher-printer-worker:**
```yaml
command: rq worker --url redis://shared-redis:6379 --path /app teacher_printer  # Change 'default' to 'teacher_printer'
environment:
  - REDIS_URL=redis://shared-redis:6379  # Add this
  - TP_QUEUE=teacher_printer             # Add this
```

## Deployment Commands

```bash
# 1. Stop services
docker-compose down

# 2. Pull latest image (after rebuilding with new code)
docker pull simond3414/teacher-printer:latest

# 3. Start services
docker-compose up -d

# 4. Verify worker queue
docker-compose logs teacher-printer-worker | grep Listening
# Should show: "Listening on teacher_printer..."

# 5. Monitor logs
docker-compose logs -f teacher-printer-worker
```

## Verification

```bash
# Check environment variables
docker-compose exec teacher-printer env | grep -E '(REDIS_URL|TP_QUEUE)'
docker-compose exec teacher-printer-worker env | grep -E '(REDIS_URL|TP_QUEUE)'

# Check Redis connectivity
docker-compose exec teacher-printer-worker redis-cli -h shared-redis ping
# Should return: PONG

# View RQ Dashboard
# Open: http://your-server:9181
# Look for: "teacher_printer" queue
```

## Build & Push Updated Image

```bash
# From project directory
docker build -t simond3414/teacher-printer:latest .
docker push simond3414/teacher-printer:latest
```

## What Changed

| Aspect | Before | After |
|--------|--------|-------|
| Queue name | `default` | `teacher_printer` |
| Config | `REDIS_HOST` + `REDIS_PORT` | `REDIS_URL` |
| Enqueue | Direct `queue.enqueue()` | Helper functions |
| Worker command | `... default` | `... teacher_printer` |
| Job IDs | Random | Prefixed: `tp:{job_id}:{type}` |
| Retry logic | None | 3 attempts, [10s, 30s, 60s] |

## Files Modified

- ✅ `modules/queue_config.py` - New centralized config
- ✅ `app.py` - Updated to use helpers
- 📝 `DOCKER_COMPOSE_UPDATE.md` - Full deployment guide
- 📝 `MIGRATION_SUMMARY.md` - Complete change summary
