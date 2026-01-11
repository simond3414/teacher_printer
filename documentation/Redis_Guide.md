# Redis Background Jobs Guide for Streamlit Apps

A practical guide for adding Redis Queue (RQ) background job processing to Streamlit applications, based on the teacher-printer implementation.

## Architecture Overview

```
┌─────────────────┐     Jobs      ┌─────────────┐
│  Streamlit UI   │──────────────▶│    Redis    │
│   (Lightweight) │               │   (Broker)  │
└─────────────────┘               └─────────────┘
                                         │
                                         │ Pick jobs
                                         ▼
                                  ┌─────────────┐
                                  │ RQ Worker   │
                                  │ (Heavy CPU) │
                                  └─────────────┘
```

**Key Benefits:**
- UI stays responsive during heavy processing
- Can close Streamlit - jobs continue running
- Worker processes one job at a time (controlled resource usage)
- Easy to scale workers independently

---

## Step-by-Step Implementation

### 1. Add Dependencies

```bash
# requirements.txt
redis==5.0.1
rq==1.16.2
```

### 2. Create Worker Module

Create `worker.py` with your heavy processing functions:

```python
"""
Background worker for heavy processing tasks.
"""
import gc
from datetime import datetime
from rq import get_current_job

def my_heavy_task(arg1, arg2, arg3):
    """
    Background task example.
    
    Args:
        arg1, arg2, arg3: Your parameters (positional args preferred)
    
    Returns:
        dict: Result with success status and details
    """
    rq_job = get_current_job()
    
    try:
        # Update progress (optional)
        if rq_job:
            rq_job.meta['progress'] = 0
            rq_job.meta['status'] = 'Starting...'
            rq_job.save_meta()
        
        # Log start
        print(f"[{datetime.now()}] WORKER: Task started")
        
        # DO YOUR HEAVY WORK HERE
        result = do_something_expensive(arg1, arg2, arg3)
        
        # Update progress
        if rq_job:
            rq_job.meta['progress'] = 100
            rq_job.meta['status'] = 'Complete'
            rq_job.save_meta()
        
        # Log completion
        print(f"[{datetime.now()}] WORKER: Task completed")
        
        # Clean up memory
        gc.collect()
        
        return {
            'success': True,
            'message': 'Task completed',
            'result': result
        }
    
    except Exception as e:
        if rq_job:
            rq_job.meta['status'] = f'Error: {str(e)}'
            rq_job.save_meta()
        
        return {
            'success': False,
            'message': str(e)
        }
```

**Key Points:**
- Use positional arguments (not keyword args) - makes RQ enqueue simpler
- Return dict with `success` and relevant data
- Use `get_current_job()` for progress updates (optional)
- Call `gc.collect()` after heavy operations
- Add logging for debugging

### 3. Modify Streamlit App

Add Redis connection and job submission to your `app.py`:

```python
import streamlit as st
import os
from redis import Redis
from rq import Queue
from rq.job import Job
import worker  # Import your worker module

# Redis configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

@st.cache_resource
def get_redis_connection():
    """Get Redis connection with caching."""
    try:
        redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
        redis_conn.ping()
        return redis_conn
    except Exception as e:
        st.error(f"⚠️ Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        st.info("Make sure Redis is running: `docker run -d -p 6379:6379 redis:7-alpine`")
        return None

def get_queue():
    """Get RQ queue instance."""
    redis_conn = get_redis_connection()
    if redis_conn:
        return Queue('default', connection=redis_conn)
    return None

# Initialize pending jobs in session state
if 'pending_jobs' not in st.session_state:
    st.session_state.pending_jobs = {}

# Submit a job
queue = get_queue()
if queue:
    rq_job = queue.enqueue(
        worker.my_heavy_task,  # Function object (not string!)
        arg1_value,            # Positional args
        arg2_value,
        arg3_value,
        job_timeout='10m'      # Timeout
    )
    
    # Track job in session state
    st.session_state.pending_jobs[f"unique_key"] = {
        'rq_job_id': rq_job.id,
        'type': 'task_description',
        'display_name': 'User-friendly name'
    }
    
    st.success("✅ Job submitted! Processing in background...")
```

### 4. Add Job Status Monitoring (Optional)

In your sidebar or main area:

```python
# Display pending jobs
if st.session_state.pending_jobs:
    st.subheader("🔄 Background Jobs")
    
    # Manual refresh button
    if st.button("🔄 Refresh Job Status"):
        st.rerun()
    
    redis_conn = get_redis_connection()
    if redis_conn:
        completed_jobs = []
        
        for job_key, job_info in st.session_state.pending_jobs.items():
            try:
                rq_job = Job.fetch(job_info['rq_job_id'], connection=redis_conn)
                status = rq_job.get_status()
                
                if status == 'finished':
                    st.success(f"✅ {job_info['display_name']} complete!")
                    completed_jobs.append(job_key)
                    result = rq_job.result
                    # Use result as needed
                
                elif status == 'failed':
                    st.error(f"❌ {job_info['display_name']} failed")
                    completed_jobs.append(job_key)
                    if rq_job.exc_info:
                        with st.expander("Error details"):
                            st.code(rq_job.exc_info)
                
                elif status in ['queued', 'started']:
                    meta = rq_job.meta
                    progress = meta.get('progress', 0)
                    st.info(f"⏳ {job_info['display_name']}")
                    if progress > 0:
                        st.progress(progress / 100)
            
            except Exception as e:
                st.warning(f"⚠️ Cannot check job: {str(e)}")
                completed_jobs.append(job_key)
        
        # Remove completed jobs
        for job_key in completed_jobs:
            del st.session_state.pending_jobs[job_key]
```

### 5. Docker Compose Configuration

Update `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  web:
    build: .
    ports:
      - "8501:8501"  # Or your Streamlit port
    volumes:
      - ./your_data:/app/your_data
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    deploy:
      resources:
        limits:
          memory: 512M   # Lightweight UI
          cpus: '0.5'
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  worker:
    build: .
    command: rq worker --url redis://redis:6379 default
    volumes:
      - ./your_data:/app/your_data  # Same volumes as web
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    deploy:
      resources:
        limits:
          memory: 1536M  # Heavy processing
          cpus: '1.0'
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
```

**Resource Guidelines:**
- **Redis**: 256MB, 0.25 CPU (minimal)
- **Web UI**: 512MB, 0.5 CPU (responsive interface)
- **Worker**: 1.5GB+, 1.0 CPU (adjust based on your processing needs)

### 6. Environment Variables

Create `.env.example`:

```bash
# Redis Configuration
REDIS_HOST=localhost  # Use 'redis' in docker-compose
REDIS_PORT=6379

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

---

## Development Workflow

### Local Development (Laptop)

1. **Start Redis in Docker:**
   ```bash
   docker run -d --name redis-local -p 6379:6379 redis:7-alpine
   ```

2. **Terminal 1 - Worker:**
   ```bash
   source .venv/bin/activate
   export REDIS_HOST=localhost REDIS_PORT=6379
   rq worker --url redis://localhost:6379 default
   ```

3. **Terminal 2 - Streamlit:**
   ```bash
   source .venv/bin/activate
   export REDIS_HOST=localhost REDIS_PORT=6379
   streamlit run app.py
   ```

### Production (Docker Compose)

```bash
# Start all services
docker-compose up --build -d

# Check status
docker-compose ps

# View worker logs
docker-compose logs -f worker

# Stop all
docker-compose down
```

---

## Testing Your Implementation

Create `test_redis.py`:

```python
from redis import Redis
from rq import Queue
import worker

# Test connection
redis_conn = Redis(host='localhost', port=6379)
redis_conn.ping()
print("✅ Redis connected")

# Test job submission
queue = Queue('default', connection=redis_conn)
job = queue.enqueue(worker.my_heavy_task, arg1, arg2, arg3)
print(f"✅ Job submitted: {job.id}")
print(f"   Status: {job.get_status()}")
```

---

## Common Patterns

### Pattern 1: File Processing
```python
# worker.py
def process_file(file_path, output_path):
    # Process file
    return {'success': True, 'output': output_path}

# app.py
uploaded = st.file_uploader("Upload")
if uploaded:
    file_path = save_file(uploaded)
    queue.enqueue(worker.process_file, file_path, output_path)
```

### Pattern 2: Multiple Job Types
```python
# Track job type in session state
st.session_state.pending_jobs[f"{job_id}_process"] = {
    'rq_job_id': rq_job.id,
    'type': 'file_processing',
    'display_name': filename
}

st.session_state.pending_jobs[f"{job_id}_export"] = {
    'rq_job_id': rq_job.id,
    'type': 'export',
    'display_name': f"Export {filename}"
}
```

### Pattern 3: Job Chaining
```python
# In worker.py
from rq import get_current_queue

def task_one(data):
    result = process(data)
    # Queue next task
    queue = get_current_queue()
    queue.enqueue(task_two, result)
    return {'success': True}
```

---

## Troubleshooting

### Redis connection failed
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
docker exec <redis-container> redis-cli ping
# Should return: PONG
```

### Worker not picking up jobs
```bash
# Check worker logs
docker-compose logs worker

# Verify queue has jobs
docker exec <redis-container> redis-cli LLEN rq:queue:default
```

### Clear stuck jobs
```bash
# Clear all Redis data (caution!)
docker exec <redis-container> redis-cli FLUSHDB
```

### TypeError: missing arguments
- Make sure you're passing **function objects** not strings
- Use **positional arguments** not keyword arguments
- Check function signature matches enqueue call

---

## Security Notes

- **Never expose Redis to internet without authentication**
- In production, use Redis password: `redis://:password@redis:6379`
- Consider using Redis Sentinel for high availability
- Use Docker networks to isolate Redis from external access

---

## Performance Tips

1. **Memory**: Monitor worker memory usage and adjust limits
2. **Timeouts**: Set appropriate `job_timeout` for long tasks
3. **Concurrency**: Run multiple workers if tasks are I/O bound
4. **Cleanup**: Always call `gc.collect()` after heavy processing
5. **Logging**: Use structured logging to debug issues

---

## Summary Checklist

- [ ] Add `redis` and `rq` to requirements.txt
- [ ] Create `worker.py` with processing functions (use positional args)
- [ ] Import `worker` module in app.py
- [ ] Add Redis connection functions to app.py
- [ ] Replace blocking operations with `queue.enqueue(worker.function, args...)`
- [ ] Store job IDs in `st.session_state.pending_jobs`
- [ ] Add manual refresh button for job status
- [ ] Update docker-compose.yml with three services
- [ ] Set resource limits (web: 512MB, worker: 1.5GB)
- [ ] Test locally with Docker Redis before deploying
- [ ] Monitor worker logs for errors

---

## Example: Full Minimal Implementation

**worker.py:**
```python
def process_data(data_path):
    import time
    time.sleep(5)  # Simulate work
    return {'success': True, 'rows': 1000}
```

**app.py:**
```python
import streamlit as st
from redis import Redis
from rq import Queue
import worker

@st.cache_resource
def get_queue():
    conn = Redis(host='localhost', port=6379)
    return Queue('default', connection=conn)

if 'pending_jobs' not in st.session_state:
    st.session_state.pending_jobs = {}

if st.button("Process"):
    queue = get_queue()
    job = queue.enqueue(worker.process_data, "data.csv")
    st.session_state.pending_jobs['job1'] = {
        'rq_job_id': job.id,
        'type': 'processing',
        'display_name': 'Data Processing'
    }
    st.success("Job submitted!")
```

That's it! You now have a responsive Streamlit app with background processing.
