# Purpose: handle job lifecycle and file operations.

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

JOBS_BASE_DIR = 'printer_processes'

def create_job(pdf_source, friendly_name=None):
    """Create a new job with unique ID and folder structure.
    
    Args:
        pdf_source (str): Path to source PDF file
        friendly_name (str, optional): User-friendly job name for display
    
    Returns:
        tuple: (job_id, job_folder) or (None, error_message)
    """
    try:
        # Generate unique job ID
        job_id = get_job_id()
        friendly_label = friendly_name.strip() if friendly_name and friendly_name.strip() else None
        
        # Create job folder structure
        job_folder = os.path.join(JOBS_BASE_DIR, job_id)
        images_folder = os.path.join(job_folder, 'images')
        thumbnails_folder = os.path.join(job_folder, 'thumbnails')
        
        os.makedirs(images_folder, exist_ok=True)
        os.makedirs(thumbnails_folder, exist_ok=True)
        
        # Copy PDF to job folder
        dest_pdf = os.path.join(job_folder, 'original.pdf')
        shutil.copy2(pdf_source, dest_pdf)
        
        # Create empty selections file
        selections_path = os.path.join(job_folder, 'selections.json')
        with open(selections_path, 'w') as f:
            json.dump({}, f)
        
        # Save job metadata for UI display
        metadata = {
            'job_id': job_id,
            'friendly_name': friendly_label,
            'created_at': datetime.now().isoformat(),
            'pdf_name': os.path.basename(pdf_source)
        }
        metadata_path = os.path.join(job_folder, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        # Debug: Log job creation
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        job_display = friendly_label if friendly_label else job_id
        print(f"[{timestamp}] NEW JOB CREATED: {job_display} (ID: {job_id})")
        
        return job_id, job_folder
    
    except Exception as e:
        return None, f"Error creating job: {str(e)}"

def get_job_id():
    """Generate timestamp-based unique job ID.
    
    Returns:
        str: Unique job ID (e.g., 'job_20251226_092049')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"job_{timestamp}"

def _load_metadata(job_folder):
    """Best-effort metadata loader for a job folder."""
    metadata_path = os.path.join(job_folder, 'metadata.json')
    if not os.path.exists(metadata_path):
        return {}
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def list_jobs():
    """Return list of all job IDs from inputs folder.
    
    Returns:
        list: List of job_id strings
    """
    inputs_dir = JOBS_BASE_DIR
    if not os.path.exists(inputs_dir):
        return []
    
    jobs = []
    for item in os.listdir(inputs_dir):
        item_path = os.path.join(inputs_dir, item)
        if os.path.isdir(item_path) and item.startswith('job_'):
            jobs.append(item)
    
    return sorted(jobs, reverse=True)  # Most recent first

def get_job_info(job_id):
    """Return metadata about a job.
    
    Args:
        job_id (str): Job identifier
    
    Returns:
        dict: Job metadata or None if job doesn't exist
    """
    job_folder = os.path.join(JOBS_BASE_DIR, job_id)
    if not os.path.exists(job_folder):
        return None
    
    pdf_path = os.path.join(job_folder, 'original.pdf')
    images_folder = os.path.join(job_folder, 'images')
    selections_path = os.path.join(job_folder, 'selections.json')
    metadata = _load_metadata(job_folder)
    friendly_name = metadata.get('friendly_name') or None
    created_raw = metadata.get('created_at')
    created_display = None
    if created_raw:
        try:
            created_display = datetime.fromisoformat(created_raw).strftime('%Y-%m-%d %H:%M')
        except Exception:
            created_display = created_raw
    else:
        created_display = job_id.replace('job_', '').replace('_', ' ')
    
    # Count images
    image_count = 0
    if os.path.exists(images_folder):
        image_count = len([f for f in os.listdir(images_folder) if f.endswith('.jpg')])
    
    # Count selections
    selections_count = 0
    if os.path.exists(selections_path):
        with open(selections_path, 'r') as f:
            selections = json.load(f)
            selections_count = len(selections)
    
    # Calculate progress
    progress = 0
    if image_count > 0:
        progress = round((selections_count / image_count) * 100, 1)
    
    # Get DPI from metadata if available
    dpi = metadata.get('dpi', None)
    
    return {
        'job_id': job_id,
        'pdf_name': 'original.pdf',
        'pdf_exists': os.path.exists(pdf_path),
        'image_count': image_count,
        'selections_count': selections_count,
        'progress_percent': progress,
        'created': created_display,
        'friendly_name': friendly_name,
        'dpi': dpi
    }

def delete_job(job_id):
    """Remove job folder from inputs, processes, and outputs.
    
    Args:
        job_id (str): Job identifier
    
    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        deleted = []
        folders = ['printer_inputs', 'printer_processes', 'printer_outputs']
        
        for folder in folders:
            job_path = os.path.join(folder, job_id)
            if os.path.exists(job_path):
                shutil.rmtree(job_path)
                deleted.append(folder)
        
        # Also check for output PDF
        output_pdf = os.path.join('printer_outputs', f"{job_id}.pdf")
        if os.path.exists(output_pdf):
            os.remove(output_pdf)
            deleted.append('output PDF')
        
        if deleted:
            return True, f"Deleted job from: {', '.join(deleted)}"
        else:
            return False, "Job not found in any folder"
    
    except Exception as e:
        return False, f"Error deleting job: {str(e)}"

def delete_all_jobs():
    """Delete all jobs from printer_processes directory.
    
    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        jobs = list_jobs()
        if not jobs:
            return False, "No jobs to delete"
        
        deleted_count = 0
        failed_count = 0
        
        for job_id in jobs:
            success, _ = delete_job(job_id)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
        
        if failed_count > 0:
            return True, f"Deleted {deleted_count} jobs ({failed_count} failed)"
        else:
            return True, f"Successfully deleted all {deleted_count} jobs"
    
    except Exception as e:
        return False, f"Error deleting all jobs: {str(e)}"

def get_job_paths(job_id):
    """Return dict of all relevant paths for a job.
    
    Args:
        job_id (str): Job identifier
    
    Returns:
        dict: Paths for job resources
    """
    return {
        'job_folder': os.path.join(JOBS_BASE_DIR, job_id),
        'pdf': os.path.join(JOBS_BASE_DIR, job_id, 'original.pdf'),
        'selections': os.path.join(JOBS_BASE_DIR, job_id, 'selections.json'),
        'images': os.path.join(JOBS_BASE_DIR, job_id, 'images'),
        'thumbnails': os.path.join(JOBS_BASE_DIR, job_id, 'thumbnails'),
        'output': os.path.join('printer_outputs', f"{job_id}.pdf")
    }