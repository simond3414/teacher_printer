"""
Centralized queue configuration for Teacher Printer RQ tasks.

This module provides queue management and job enqueuing functions
using a dedicated 'teacher_printer' queue to avoid conflicts with
other applications sharing the same Redis instance.
"""

import os
from redis import Redis
from rq import Queue, Retry


# Environment configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TP_QUEUE = os.getenv("TP_QUEUE", "teacher_printer")


def get_tp_queue(default_timeout=900):
    """
    Get the Teacher Printer RQ queue instance.
    
    Args:
        default_timeout (int): Default timeout in seconds for jobs (default: 900 = 15 min)
    
    Returns:
        Queue: RQ Queue instance configured for teacher_printer
    """
    conn = Redis.from_url(REDIS_URL)
    return Queue(
        name=TP_QUEUE,
        connection=conn,
        default_timeout=default_timeout,
    )


def enqueue_generate_output_pdf(job_id, selections, output_path):
    """
    Enqueue a PDF generation job.
    
    Args:
        job_id (str): Job identifier
        selections (dict): Image to page number mappings
        output_path (str): Path for output PDF
    
    Returns:
        Job: RQ Job instance
    """
    q = get_tp_queue()
    return q.enqueue(
        "worker.generate_output_pdf",
        job_id,
        selections,
        output_path,
        job_id=f"tp:{job_id}:pdf",
        job_timeout=1800,              # 30 minutes per-job timeout
        retry=Retry(max=3, interval=[10, 30, 60]),
        result_ttl=600,                # Keep results for 10 minutes
        failure_ttl=86400,             # Keep failures for 24 hours
        description=f"TP generate PDF {job_id}",
    )


def enqueue_process_zip(job_id, zip_path, filenames, dpi=200):
    """
    Enqueue a ZIP to images conversion job.
    
    Args:
        job_id (str): Job identifier
        zip_path (str): Path to ZIP file
        filenames (list): List of PDF filenames to extract
        dpi (int): Resolution for conversion (default: 200)
    
    Returns:
        Job: RQ Job instance
    """
    q = get_tp_queue()
    return q.enqueue(
        "worker.process_zip_to_images",
        job_id,
        zip_path,
        filenames,
        dpi,
        job_id=f"tp:{job_id}:zip",
        job_timeout=3600,              # 60 minutes per-job timeout
        retry=Retry(max=3, interval=[10, 30, 60]),
        result_ttl=600,                # Keep results for 10 minutes
        failure_ttl=86400,             # Keep failures for 24 hours
        description=f"TP zip2img {job_id}",
    )


def enqueue_process_pdf(job_id, pdf_path, dpi=200):
    """
    Enqueue a PDF to images conversion job.
    
    Args:
        job_id (str): Job identifier
        pdf_path (str): Path to PDF file
        dpi (int): Resolution for conversion (default: 200)
    
    Returns:
        Job: RQ Job instance
    """
    q = get_tp_queue()
    return q.enqueue(
        "worker.process_pdf_to_images",
        job_id,
        pdf_path,
        dpi,
        job_id=f"tp:{job_id}:convert",
        job_timeout=600,               # 10 minutes per-job timeout
        retry=Retry(max=3, interval=[10, 30, 60]),
        result_ttl=600,                # Keep results for 10 minutes
        failure_ttl=86400,             # Keep failures for 24 hours
        description=f"TP pdf2img {job_id}",
    )
