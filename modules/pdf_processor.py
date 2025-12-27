# Purpose: convert pdf to images and manage image fidelity.

import os
import gc
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from pathlib import Path
from modules.job_manager import JOBS_BASE_DIR

def get_adaptive_dpi(pdf_path):
    """
    Calculate appropriate DPI based on PDF file size.
    Balances quality with memory constraints.
    
    Args:
        pdf_path (str): Path to PDF file
    
    Returns:
        int: Recommended DPI value
    """
    try:
        file_size_bytes = os.path.getsize(pdf_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_mb < 20:
            return 200  # High quality for small files
        elif file_size_mb < 50:
            return 175  # Good quality
        elif file_size_mb < 100:
            return 150  # Acceptable quality
        else:
            return 120  # Readable for large files
    except Exception as e:
        print(f"Warning: Could not determine file size, using default DPI: {e}")
        return 150  # Safe default

def convert_pdf_to_images(pdf_path, job_id, dpi=None):
    """Convert PDF to high-resolution images using page-by-page processing.
    
    Args:
        pdf_path (str): Path to PDF file
        job_id (str): Job identifier
        dpi (int, optional): Resolution for conversion. If None, auto-calculated based on file size.
    
    Returns:
        tuple: (success, message, image_count)
    """
    try:
        job_folder = os.path.join(JOBS_BASE_DIR, job_id)
        images_folder = os.path.join(job_folder, 'images')
        thumbnails_folder = os.path.join(job_folder, 'thumbnails')
        
        # Auto-calculate DPI if not provided
        if dpi is None:
            dpi = get_adaptive_dpi(pdf_path)
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            print(f"Auto-selected DPI: {dpi} for {file_size_mb:.1f}MB PDF")
        
        # Get total page count without loading entire PDF
        info = pdfinfo_from_path(pdf_path)
        total_pages = info["Pages"]
        
        image_count = 0
        
        # Process ONE page at a time to minimize memory usage
        for page_num in range(1, total_pages + 1):
            # Load only this single page
            pages = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=page_num,
                last_page=page_num
            )
            
            page = pages[0]
            
            # Save full-resolution image
            img_filename = f"img_{page_num:03d}.jpg"
            img_path = os.path.join(images_folder, img_filename)
            page.save(img_path, 'JPEG', quality=85)
            
            # Generate and save thumbnail
            thumb_path = os.path.join(thumbnails_folder, f"thumb_{page_num:03d}.jpg")
            generate_thumbnail(img_path, thumb_path, max_size=800)
            
            # CRITICAL: Explicit memory cleanup after each page
            page.close()
            del pages, page
            gc.collect()
            
            image_count += 1
        
        return True, f"Converted {image_count} pages at {dpi} DPI", image_count, dpi
    
    except Exception as e:
        return False, f"Error converting PDF: {str(e)}", 0, None

def generate_thumbnail(image_path, output_path, max_size=800):
    """Create lower-resolution version for UI display.
    
    Args:
        image_path (str): Path to source image
        output_path (str): Path to save thumbnail
        max_size (int): Maximum dimension in pixels
    
    Returns:
        bool: Success status
    """
    try:
        img = Image.open(image_path)
        
        # Calculate new size maintaining aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Save thumbnail
        img.save(output_path, 'JPEG', quality=85)
        return True
    
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}")
        return False

def get_image_count(job_id):
    """Return total number of images for a job.
    
    Args:
        job_id (str): Job identifier
    
    Returns:
        int: Number of images
    """
    images_folder = os.path.join(JOBS_BASE_DIR, job_id, 'images')
    if not os.path.exists(images_folder):
        return 0
    
    images = [f for f in os.listdir(images_folder) if f.endswith('.jpg')]
    return len(images)