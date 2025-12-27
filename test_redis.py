#!/usr/bin/env python3
"""
Quick test script to verify Redis and RQ are working.
"""

import os
from redis import Redis
from rq import Queue
from rq.job import Job

# Test Redis connection
print("🔍 Testing Redis connection...")
try:
    redis_conn = Redis(host='localhost', port=6379, decode_responses=False)
    redis_conn.ping()
    print("✅ Redis connection successful!")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    exit(1)

# Test Queue creation
print("\n🔍 Creating RQ queue...")
try:
    queue = Queue('default', connection=redis_conn)
    print(f"✅ Queue created: {queue.name}")
    print(f"   Jobs in queue: {len(queue)}")
except Exception as e:
    print(f"❌ Queue creation failed: {e}")
    exit(1)

# Test importing worker module
print("\n🔍 Testing worker module import...")
try:
    import worker
    print(f"✅ Worker module imported")
    print(f"   Available functions: {[f for f in dir(worker) if not f.startswith('_')]}")
except Exception as e:
    print(f"❌ Worker import failed: {e}")
    exit(1)

# Test job submission with real worker function
print("\n🔍 Testing job submission with worker.process_pdf_to_images...")
try:
    # This will fail without a real job_id, but tests if we can submit
    job = queue.enqueue('worker.process_pdf_to_images', 
                       job_id='test_job',
                       pdf_path='/fake/path.pdf',
                       dpi=200,
                       job_timeout='10m')
    print(f"✅ Job submitted: {job.id}")
    print(f"   Status: {job.get_status()}")
    print(f"   Function: {job.func_name}")
    print(f"   Jobs in queue now: {len(queue)}")
except Exception as e:
    print(f"❌ Job submission failed: {e}")
    exit(1)

print("\n✨ All tests passed! Ready to run worker and app.")
print("\nNext steps:")
print("  Terminal 1: REDIS_HOST=localhost REDIS_PORT=6379 rq worker --url redis://localhost:6379 default")
print("  Terminal 2: REDIS_HOST=localhost REDIS_PORT=6379 streamlit run app.py --server.port=8507")
