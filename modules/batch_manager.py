# Purpose: convert images into batches and manage selections.

import os
import json
from pathlib import Path
from modules.job_manager import JOBS_BASE_DIR

def create_batches(total_images, batch_size=20):
    """Return list of batch ranges.
    
    Args:
        total_images (int): Total number of images
        batch_size (int): Images per batch (default 20)
    
    Returns:
        list: List of tuples [(start, end), ...]
    """
    batches = []
    for start in range(0, total_images, batch_size):
        end = min(start + batch_size, total_images)
        batches.append((start, end))
    return batches

def get_batch_images(job_id, batch_start, batch_end):
    """Return list of image paths for a batch.
    
    Args:
        job_id (str): Job identifier
        batch_start (int): Starting index (0-based)
        batch_end (int): Ending index (exclusive)
    
    Returns:
        dict: Dict with 'images' and 'thumbnails' lists
    """
    images_folder = os.path.join(JOBS_BASE_DIR, job_id, 'images')
    thumbnails_folder = os.path.join(JOBS_BASE_DIR, job_id, 'thumbnails')
    
    batch_images = []
    batch_thumbnails = []
    
    for i in range(batch_start + 1, batch_end + 1):
        img_name = f"img_{i:03d}.jpg"
        thumb_name = f"thumb_{i:03d}.jpg"
        
        img_path = os.path.join(images_folder, img_name)
        thumb_path = os.path.join(thumbnails_folder, thumb_name)
        
        if os.path.exists(thumb_path):
            batch_images.append(img_path)
            batch_thumbnails.append(thumb_path)
    
    return {
        'images': batch_images,
        'thumbnails': batch_thumbnails,
        'image_numbers': list(range(batch_start + 1, batch_end + 1))
    }

def load_selections(job_id):
    """Load JSON with image to page number and rotation mappings.
    
    Supports both legacy format {img_key: page_num} and 
    new format {img_key: {"page": page_num, "rotation": degrees}}
    
    Args:
        job_id (str): Job identifier
    
    Returns:
        dict: Selections dictionary with normalized format {img_key: {"page": N, "rotation": D}}
    """
    selections_path = os.path.join(JOBS_BASE_DIR, job_id, 'selections.json')
    
    if not os.path.exists(selections_path):
        return {}
    
    try:
        with open(selections_path, 'r') as f:
            raw_data = json.load(f)
        
        # Normalize to new format
        normalized = {}
        for img_key, value in raw_data.items():
            if isinstance(value, dict):
                # New format
                normalized[img_key] = {
                    'page': value.get('page', 1),
                    'rotation': value.get('rotation', 0)
                }
            else:
                # Legacy format (integer page number)
                normalized[img_key] = {
                    'page': value if value is not None else 1,
                    'rotation': 0
                }
        return normalized
    
    except Exception as e:
        print(f"Error loading selections: {e}")
        return {}

def save_selections(job_id, selections_dict):
    """Save selections to JSON in new format.
    
    Args:
        job_id (str): Job identifier
        selections_dict (dict): Image to page and rotation mappings
    
    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        selections_path = os.path.join(JOBS_BASE_DIR, job_id, 'selections.json')
        
        # Ensure all values are in new format
        formatted = {}
        for img_key, value in selections_dict.items():
            if isinstance(value, dict):
                formatted[img_key] = {
                    'page': value.get('page', 1),
                    'rotation': value.get('rotation', 0)
                }
            else:
                # Legacy integer format
                formatted[img_key] = {
                    'page': value if value is not None else 1,
                    'rotation': 0
                }
        
        with open(selections_path, 'w') as f:
            json.dump(formatted, f, indent=2)
        
        return True, "Selections saved successfully"
    
    except Exception as e:
        return False, f"Error saving selections: {str(e)}"

def get_page_number(selections_dict, img_key):
    """Extract page number from selection value.
    
    Args:
        selections_dict (dict): Selections dictionary
        img_key (str): Image key (e.g., "img_001")
    
    Returns:
        int: Page number
    """
    value = selections_dict.get(img_key, {})
    if isinstance(value, dict):
        return value.get('page', 1)
    return value if value is not None else 1


def get_rotation(selections_dict, img_key):
    """Extract rotation from selection value.
    
    Args:
        selections_dict (dict): Selections dictionary
        img_key (str): Image key (e.g., "img_001")
    
    Returns:
        int: Rotation in degrees (0, 90, 180, or 270)
    """
    value = selections_dict.get(img_key, {})
    if isinstance(value, dict):
        return value.get('rotation', 0)
    return 0


def set_rotation(selections_dict, img_key, rotation):
    """Set rotation for an image, normalizing to 0-270.
    
    Args:
        selections_dict (dict): Selections dictionary to modify
        img_key (str): Image key (e.g., "img_001")
        rotation (int): Rotation angle in degrees
    
    Returns:
        dict: Updated selections dictionary
    """
    # Normalize rotation to 0, 90, 180, 270
    rotation = rotation % 360
    if rotation not in [0, 90, 180, 270]:
        rotation = 0
    
    if img_key not in selections_dict:
        selections_dict[img_key] = {'page': 1, 'rotation': rotation}
    elif isinstance(selections_dict[img_key], dict):
        selections_dict[img_key]['rotation'] = rotation
    else:
        # Convert from legacy format
        selections_dict[img_key] = {
            'page': selections_dict[img_key],
            'rotation': rotation
        }
    
    return selections_dict


def get_batch_selection_status(job_id, batch_num, total_batches, batch_size=4):
    """Check if batch has been completed.
    
    Args:
        job_id (str): Job identifier
        batch_num (int): Current batch number (0-based)
        total_batches (int): Total number of batches
        batch_size (int): Images per batch (default 4)
    
    Returns:
        dict: Status information
    """
    from modules.pdf_processor import get_image_count
    
    total_images = get_image_count(job_id)
    selections = load_selections(job_id)
    
    # Calculate batch range
    batch_start = batch_num * batch_size
    batch_end = min(batch_start + batch_size, total_images)
    
    # Check how many in this batch have selections
    batch_complete = 0
    for i in range(batch_start + 1, batch_end + 1):
        img_key = f"img_{i:03d}"
        if img_key in selections:
            batch_complete += 1
    
    batch_total = batch_end - batch_start
    
    return {
        'batch_num': batch_num + 1,
        'total_batches': total_batches,
        'batch_complete': batch_complete,
        'batch_total': batch_total,
        'batch_percent': round((batch_complete / batch_total) * 100) if batch_total > 0 else 0,
        'overall_complete': len(selections),
        'overall_total': total_images,
        'overall_percent': round((len(selections) / total_images) * 100) if total_images > 0 else 0
    }