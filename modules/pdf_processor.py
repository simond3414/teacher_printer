# Purpose: convert pdf to images and manage image fidelity.

import os
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from modules.job_manager import JOBS_BASE_DIR

def convert_pdf_to_images(pdf_path, job_id, dpi=200):
    """Convert PDF to high-resolution images.
    
    Args:
        pdf_path (str): Path to PDF file
        job_id (str): Job identifier
        dpi (int): Resolution for conversion (default 200)
    
    Returns:
        tuple: (success, message, image_count)
    """
    try:
        job_folder = os.path.join(JOBS_BASE_DIR, job_id)
        images_folder = os.path.join(job_folder, 'images')
        thumbnails_folder = os.path.join(job_folder, 'thumbnails')
        
        # Convert PDF to images
        pages = convert_from_path(pdf_path, dpi=dpi)
        
        image_count = 0
        for i, page in enumerate(pages, start=1):
            # Save full-resolution image
            img_filename = f"img_{i:03d}.png"
            img_path = os.path.join(images_folder, img_filename)
            page.save(img_path, 'PNG')
            
            # Generate and save thumbnail
            thumb_path = os.path.join(thumbnails_folder, f"thumb_{i:03d}.png")
            generate_thumbnail(img_path, thumb_path, max_size=800)
            
            image_count += 1
        
        return True, f"Converted {image_count} pages", image_count
    
    except Exception as e:
        return False, f"Error converting PDF: {str(e)}", 0

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
        img.save(output_path, 'PNG', optimize=True)
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
    
    images = [f for f in os.listdir(images_folder) if f.endswith('.png')]
    return len(images)