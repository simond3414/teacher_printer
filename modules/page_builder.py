# Purpose: generate output PDF with flexible layouts.

import os
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from modules.job_manager import JOBS_BASE_DIR

def build_output_pdf(job_id, selections_dict, output_path):
    """Main function to create output PDF.
    
    Args:
        job_id (str): Job identifier
        selections_dict (dict): Image to page number mappings
        output_path (str): Path for output PDF
    
    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        # Debug: Log PDF generation start
        from datetime import datetime
        from modules.job_manager import _load_metadata, JOBS_BASE_DIR
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        job_folder = os.path.join(JOBS_BASE_DIR, job_id)
        metadata = _load_metadata(job_folder)
        job_display = metadata.get('friendly_name') or job_id
        print(f"[{timestamp}] PDF GENERATION STARTED: {job_display} (ID: {job_id})")
        
        # Delete existing PDF to ensure fresh generation
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # Group images by page
        pages_dict = group_images_by_page(selections_dict)
        
        if not pages_dict:
            return False, "No images to include in PDF (all excluded?)"
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=A4)
        a4_width, a4_height = A4
        
        images_folder = os.path.join(JOBS_BASE_DIR, job_id, 'images')
        
        # Process each output page
        for page_num in sorted(pages_dict.keys()):
            image_names = pages_dict[page_num]
            layout = get_layout(len(image_names))
            
            # Create page with images
            create_page_with_images(
                c, 
                images_folder, 
                image_names, 
                layout, 
                a4_width, 
                a4_height
            )
            
            c.showPage()  # Next page
        
        c.save()
        
        # Debug: Log PDF generation completion
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        print(f"[{timestamp}] PDF GENERATION COMPLETED: {job_display} - {len(pages_dict)} pages")
        
        return True, f"PDF created with {len(pages_dict)} pages"
    
    except Exception as e:
        return False, f"Error building PDF: {str(e)}"

def group_images_by_page(selections_dict):
    """Group images by output page number.
    
    Args:
        selections_dict (dict): {img_001: 1, img_002: 1, img_003: 2, ...}
                                Page 0 = excluded from PDF
    
    Returns:
        dict: {1: [img_001, img_002], 2: [img_003], ...} with sorted image names
    """
    pages_dict = {}
    
    for img_name, page_num in selections_dict.items():
        if page_num == 0:  # Skip excluded images
            continue
        if page_num not in pages_dict:
            pages_dict[page_num] = []
        pages_dict[page_num].append(img_name)
    
    # Sort image names within each page to ensure consistent order
    for page_num in pages_dict:
        try:
            pages_dict[page_num].sort(key=lambda x: int(x.split('_')[1]))
        except (ValueError, IndexError):
            pages_dict[page_num].sort()  # Fallback to alphabetical
    
    return pages_dict

def get_layout(image_count):
    """Determine grid layout based on image count.
    
    Args:
        image_count (int): Number of images for this page
    
    Returns:
        tuple: (rows, cols) grid layout
    """
    if image_count == 1:
        return (1, 1)
    elif image_count == 2:
        return (2, 1)  # Stack vertically after rotation - rotated images are landscape
    elif image_count <= 4:
        return (2, 2)
    elif image_count <= 6:
        return (3, 2)
    else:  # 7-9
        return (3, 3)

def create_page_with_images(c, images_folder, image_names, layout, a4_width, a4_height):
    """Arrange images on A4 page using ReportLab.
    
    Args:
        c: ReportLab canvas object
        images_folder (str): Path to images folder
        image_names (list): List of image filenames
        layout (tuple): (rows, cols) grid layout
        a4_width (float): A4 width in points
        a4_height (float): A4 height in points
    """
    rows, cols = layout
    margin = 10 * mm
    
    # Calculate cell dimensions
    available_width = a4_width - (2 * margin)
    available_height = a4_height - (2 * margin)
    
    cell_width = available_width / cols
    cell_height = available_height / rows
    
    # Place images
    for idx, img_name in enumerate(image_names):
        row = idx // cols
        col = idx % cols
        
        img_path = os.path.join(images_folder, f"{img_name}.jpg")
        
        if os.path.exists(img_path):
            # Calculate position (PDF origin is bottom-left)
            x = margin + (col * cell_width)
            y = a4_height - margin - ((row + 1) * cell_height)
            
            # Open image to get dimensions
            img = Image.open(img_path)
            
            # Rotate image 90 degrees clockwise for 2-image horizontal layout
            if len(image_names) == 2:
                img = img.rotate(-90, expand=True)
                # Wrap rotated image for reportlab
                img_for_draw = ImageReader(img)
            else:
                # Use original file path for non-rotated images
                img_for_draw = img_path
            
            img_width, img_height = img.size
            aspect = img_width / img_height
            
            # Calculate scaled dimensions to fit cell while maintaining aspect
            if aspect > (cell_width / cell_height):
                # Width-constrained
                draw_width = cell_width - (2 * mm)
                draw_height = draw_width / aspect
            else:
                # Height-constrained
                draw_height = cell_height - (2 * mm)
                draw_width = draw_height * aspect
            
            # Center in cell
            x_offset = (cell_width - draw_width) / 2
            y_offset = (cell_height - draw_height) / 2
            
            c.drawImage(
                img_for_draw,
                x + x_offset,
                y + y_offset,
                width=draw_width,
                height=draw_height,
                preserveAspectRatio=True
            )
    
    # Fill remaining cells with blank space if needed
    total_cells = rows * cols
    if len(image_names) < total_cells:
        # Optional: draw borders for empty cells for debugging
        pass

def create_blank_image(size=(200, 200)):
    """Generate blank placeholder image.
    
    Args:
        size (tuple): (width, height) in pixels
    
    Returns:
        PIL.Image: Blank white image
    """
    return Image.new('RGB', size, color='white')