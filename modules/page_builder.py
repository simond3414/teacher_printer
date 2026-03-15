# Purpose: generate output PDF with flexible layouts.
# 
# IMPORTANT: Without optimization, output PDFs are typically 2-3x the size of the original PDF.
# This is due to ReportLab's image embedding overhead when creating custom layouts.
# The application provides "Optimized" mode which uses PyMuPDF to compress images
# and optimize PDF structure, typically achieving 50-80% file size reduction.

import os
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from modules.job_manager import JOBS_BASE_DIR

def build_output_pdf(job_id, selections_dict, output_path, optimization_mode='optimized'):
    """Main function to create output PDF.
    
    Args:
        job_id (str): Job identifier
        selections_dict (dict): Image to page number mappings
        output_path (str): Path for output PDF
        optimization_mode (str): Optimization mode - 'optimized' or 'none'
    
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
            
            # Create page with images - pass selections_dict for rotation info
            create_page_with_images(
                c, 
                images_folder, 
                image_names, 
                layout, 
                a4_width, 
                a4_height,
                selections_dict  # Pass for rotation lookup
            )
            
            c.showPage()  # Next page
        
        c.save()
        
        # Get initial file size for comparison
        initial_size = os.path.getsize(output_path)
        print(f"Initial PDF size: {initial_size / 1024 / 1024:.1f}MB")
        
        # Apply PyMuPDF optimization if requested
        if optimization_mode != 'none':
            from modules.pdf_optimizer import (
                check_pymupdf_available, 
                optimize_pdf_aggressive
            )
            
            if check_pymupdf_available():
                temp_path = output_path + '.tmp'
                
                # Optimized mode: Structural + image downsampling with moderate settings
                success, reduction = optimize_pdf_aggressive(
                    output_path, temp_path,
                    dpi_threshold=250,  # Only process very high-DPI images
                    dpi_target=200,     # Downsample to reasonable 200 DPI
                    quality=85          # Higher JPEG quality (85 instead of 80)
                )
                mode_name = "Optimized"
                
                if success and reduction > 5:  # Only apply if saves > 5%
                    os.replace(temp_path, output_path)
                    final_size = os.path.getsize(output_path)
                    print(f"PDF optimized ({mode_name} mode): {reduction:.1f}% reduction")
                    print(f"Final PDF size: {final_size / 1024 / 1024:.1f}MB")
                else:
                    # Optimization didn't help enough, keep original
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if success:
                        print(f"Optimization minimal ({reduction:.1f}%), keeping original")
                    else:
                        print("Optimization failed or not beneficial, keeping original")
            else:
                print("PyMuPDF not available, skipping optimization")
        
        # Debug: Log PDF generation completion
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        print(f"[{timestamp}] PDF GENERATION COMPLETED: {job_display} - {len(pages_dict)} pages")
        
        return True, f"PDF created with {len(pages_dict)} pages"
    
    except Exception as e:
        return False, f"Error building PDF: {str(e)}"

def group_images_by_page(selections_dict):
    """Group images by output page number.
    
    Args:
        selections_dict (dict): {img_001: {"page": 1, "rotation": 0}, ...}
                               Page 0 = excluded from PDF
    
    Returns:
        dict: {1: [img_001, img_002], 2: [img_003], ...} with sorted image names
    """
    pages_dict = {}
    
    for img_name, value in selections_dict.items():
        # Handle both old format (int) and new format (dict)
        if isinstance(value, dict):
            page_num = value.get('page', 1)
        else:
            page_num = value if value is not None else 1
        
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

def create_page_with_images(c, images_folder, image_names, layout, a4_width, a4_height, selections_dict=None):
    """Arrange images on A4 page using ReportLab with rotation support.
    
    Args:
        c: ReportLab canvas object
        images_folder (str): Path to images folder
        image_names (list): List of image filenames
        layout (tuple): (rows, cols) grid layout
        a4_width (float): A4 width in points
        a4_height (float): A4 height in points
        selections_dict (dict, optional): Selections with rotation info {img_name: {'page': N, 'rotation': D}}
    """
    import gc
    
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
            rotated_img = None
            
            # Get user-specified rotation from selections
            user_rotation = 0
            if selections_dict and img_name in selections_dict:
                value = selections_dict[img_name]
                if isinstance(value, dict):
                    user_rotation = value.get('rotation', 0)
            
            # Apply user rotation + auto-rotation for 2-image layout
            total_rotation = user_rotation
            if len(image_names) == 2:
                total_rotation += 90  # Add 90 degrees for 2-image layout
            
            # Apply rotation if needed
            if total_rotation != 0:
                rotated_img = img.rotate(-total_rotation, expand=True)
                img_for_draw = ImageReader(rotated_img)
                img_width, img_height = rotated_img.size
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
            
            # MEMORY CLEANUP: Explicitly close and delete PIL images
            img.close()
            if rotated_img:
                rotated_img.close()
            del img
            if rotated_img:
                del rotated_img, img_for_draw
    
    # Cleanup after page complete
    gc.collect()
    
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