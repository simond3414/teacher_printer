# Queue Configuration Migration - Summary

## Problem
The RQ worker was experiencing import errors because jobs were being enqueued to the shared "default" queue, which conflicts with other applications using the same Redis instance. The errors indicated the worker couldn't find the function names like `worker.generate_output_pdf`.

## Solution
Implemented a dedicated queue configuration with:
1. A centralized queue configuration module
2. Dedicated queue name: `teacher_printer`
3. Helper functions for enqueuing jobs
4. Updated worker command to listen to the dedicated queue

## Files Changed

### 1. New File: `modules/queue_config.py`
Centralized configuration for all RQ queue operations:

**Key Features:**
- Environment-based configuration (REDIS_URL, TP_QUEUE)
- Three helper functions for enqueuing jobs:
  - `enqueue_process_pdf()` - Convert PDF to images
  - `enqueue_process_zip()` - Convert ZIP of PDFs to images
  - `enqueue_generate_output_pdf()` - Generate final PDF from selections

**Job Configuration:**
- Job timeouts: 10-60 minutes depending on task
- Retry logic: Max 3 attempts with increasing intervals [10s, 30s, 60s]
- Result TTL: 10 minutes (600s)
- Failure TTL: 24 hours (86400s)
- Job ID prefixes: `tp:{job_id}:convert`, `tp:{job_id}:zip`, `tp:{job_id}:pdf`

### 2. Updated: `app.py`
Replaced all direct queue.enqueue() calls with helper functions:

**Changes:**
- Removed `from rq import Queue`
- Added `from modules import queue_config`
- Updated `get_redis_connection()` to use `queue_config.REDIS_URL`
- Removed `get_queue()` function (no longer needed)
- Replaced 5 enqueue calls:
  1. Initial PDF upload conversion (line ~248)
  2. Retry PDF conversion button (line ~370)
  3. ZIP to images conversion (line ~621)
  4. PDF regeneration button (existing PDF) (line ~683)
  5. PDF generation button (no PDF exists) (line ~738)

**Error Handling:**
All enqueue calls now wrapped in try-except blocks with user-friendly error messages.

### 3. Documentation: `DOCKER_COMPOSE_UPDATE.md`
Complete guide for updating server configuration with:
- Updated docker-compose.yml
- Deployment steps
- Verification procedures
- Troubleshooting guide

## Environment Variables

### Required (Application & Worker):
```bash
REDIS_URL=redis://shared-redis:6379  # Full Redis connection URL
TP_QUEUE=teacher_printer             # Dedicated queue name
```

### Removed:
```bash
REDIS_HOST=shared-redis              # No longer used
REDIS_PORT=6379                      # No longer used
```

## Docker Compose Changes

### teacher-printer service:
```yaml
environment:
  - REDIS_URL=redis://shared-redis:6379  # Added
  - TP_QUEUE=teacher_printer             # Added
```

### teacher-printer-worker service:
```yaml
command: rq worker --url redis://shared-redis:6379 --path /app teacher_printer
# Changed from: ... --path /app default
environment:
  - REDIS_URL=redis://shared-redis:6379  # Added
  - TP_QUEUE=teacher_printer             # Added
```

## Testing Locally

If you want to test locally before deploying:

1. **Start Redis:**
   ```bash
   docker run -d -p 6379:6379 --name redis redis:7-alpine
   ```

2. **Set environment variables:**
   ```bash
   export REDIS_URL=redis://localhost:6379
   export TP_QUEUE=teacher_printer
   ```

3. **Start the worker:**
   ```bash
   rq worker --url redis://localhost:6379 --path . teacher_printer
   ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

5. **Verify:**
   - Worker logs should show: `Listening on teacher_printer...`
   - Upload a PDF and check it processes correctly

## Migration Checklist

- [x] Create `modules/queue_config.py`
- [x] Update `app.py` imports
- [x] Replace all enqueue calls
- [x] Add error handling for enqueue operations
- [ ] Build new Docker image
- [ ] Push to Docker Hub
- [ ] Update server docker-compose.yml
- [ ] Deploy to server
- [ ] Verify worker is listening to `teacher_printer` queue
- [ ] Test PDF upload and processing
- [ ] Check RQ Dashboard shows correct queue

## Expected Behavior After Migration

1. **Job Submission:**
   - Jobs enqueued to `teacher_printer` queue (not `default`)
   - Job IDs prefixed with `tp:` for easy identification
   - Jobs include retry logic and proper timeouts

2. **Worker Processing:**
   - Worker listens only to `teacher_printer` queue
   - Worker logs show queue name: `Listening on teacher_printer...`
   - No import errors from other applications

3. **Monitoring:**
   - RQ Dashboard shows `teacher_printer` queue
   - Job descriptions include task type and job ID
   - Failed jobs retry automatically (up to 3 times)

## Notes

- Worker functions in `worker.py` remain unchanged (top-level functions)
- The `worker.py` module must be importable by the worker process
- String references like `"worker.generate_output_pdf"` are resolved by RQ at runtime
- All jobs now have consistent retry, timeout, and TTL configuration
