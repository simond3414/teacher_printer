"""
Background worker for heavy PDF processing tasks.
This runs in a separate container with more resources (1.5GB, 1.0 CPU).
"""

import os
import gc
from datetime import datetime
from rq import get_current_job
from modules import pdf_processor, page_builder, job_manager


def process_pdf_to_images(job_id, pdf_path, dpi=200):
    """
    Background task: Convert PDF to images and thumbnails.
    
    Args:
        job_id (str): Job identifier
        pdf_path (str): Path to PDF file
        dpi (int): Resolution for conversion
    
    Returns:
        dict: Result with success status and details
    """
    rq_job = get_current_job()
    
    try:
        # Update progress
        if rq_job:
            rq_job.meta['progress'] = 0
            rq_job.meta['status'] = 'Converting PDF to images...'
            rq_job.save_meta()
        
        # Log start
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        metadata = job_manager._load_metadata(os.path.join(job_manager.JOBS_BASE_DIR, job_id))
        job_display = metadata.get('friendly_name') or job_id
        print(f"[{timestamp}] WORKER: PDF conversion started for {job_display}")
        
        # Convert PDF to images (use adaptive DPI if dpi not explicitly set)
        success, msg, count, used_dpi = pdf_processor.convert_pdf_to_images(pdf_path, job_id, dpi if dpi != 200 else None)
        
        if rq_job:
            rq_job.meta['progress'] = 100
            rq_job.meta['status'] = 'Complete'
            if used_dpi:
                rq_job.meta['dpi'] = used_dpi
            rq_job.save_meta()
        
        # Persist DPI to job metadata for permanent storage
        if success and used_dpi:
            job_folder = os.path.join(job_manager.JOBS_BASE_DIR, job_id)
            metadata_path = os.path.join(job_folder, 'metadata.json')
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = job_manager.json.load(f)
                    metadata['dpi'] = used_dpi
                    with open(metadata_path, 'w') as f:
                        job_manager.json.dump(metadata, f, indent=2)
                except Exception as e:
                    print(f"Warning: Could not save DPI to metadata: {e}")
        
        # Log completion
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        print(f"[{timestamp}] WORKER: PDF conversion completed for {job_display} - {count} images")
        
        # Clean up memory
        gc.collect()
        
        return {
            'success': success,
            'message': msg,
            'image_count': count,
            'job_id': job_id,
            'dpi': used_dpi
        }
    
    except Exception as e:
        error_msg = f"Error in PDF conversion: {str(e)}"
        print(f"[ERROR] WORKER: {error_msg}")
        
        if rq_job:
            rq_job.meta['progress'] = 100
            rq_job.meta['status'] = f'Error: {str(e)}'
            rq_job.save_meta()
        
        return {
            'success': False,
            'message': error_msg,
            'image_count': 0,
            'job_id': job_id,
            'dpi': None
        }


def generate_output_pdf(job_id, selections_dict, output_path):
    """
    Background task: Generate final PDF from selected images.
    
    Args:
        job_id (str): Job identifier
        selections_dict (dict): Image to page number mappings
        output_path (str): Path for output PDF
    
    Returns:
        dict: Result with success status and details
    """
    rq_job = get_current_job()
    
    try:
        # Update progress
        if rq_job:
            rq_job.meta['progress'] = 0
            rq_job.meta['status'] = 'Generating PDF...'
            rq_job.save_meta()
        
        # Log start
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        metadata = job_manager._load_metadata(os.path.join(job_manager.JOBS_BASE_DIR, job_id))
        job_display = metadata.get('friendly_name') or job_id
        print(f"[{timestamp}] WORKER: PDF generation started for {job_display}")
        
        # Build PDF
        success, msg = page_builder.build_output_pdf(job_id, selections_dict, output_path)
        
        if rq_job:
            rq_job.meta['progress'] = 100
            rq_job.meta['status'] = 'Complete'
            rq_job.save_meta()
        
        # Log completion
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        print(f"[{timestamp}] WORKER: PDF generation completed for {job_display}")
        
        # Clean up memory
        gc.collect()
        
        return {
            'success': success,
            'message': msg,
            'job_id': job_id,
            'output_path': output_path
        }
    
    except Exception as e:
        error_msg = f"Error in PDF generation: {str(e)}"
        print(f"[ERROR] WORKER: {error_msg}")
        
        if rq_job:
            rq_job.meta['progress'] = 100
            rq_job.meta['status'] = f'Error: {str(e)}'
            rq_job.save_meta()
        
        return {
            'success': False,
            'message': error_msg,
            'job_id': job_id,
            'output_path': output_path
        }


# Note: RQ worker will automatically discover functions in this module
# Run with: rq worker --with-scheduler
