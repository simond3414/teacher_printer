# Purpose: shared helped functions.

import os
import shutil
from pathlib import Path
import PyPDF2

def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = ['printer_inputs', 'printer_processes', 'printer_outputs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def get_file_size_mb(path):
    """Return file size in MB.
    
    Args:
        path (str): Path to file
    
    Returns:
        float: File size in MB
    """
    if not os.path.exists(path):
        return 0
    size_bytes = os.path.getsize(path)
    return round(size_bytes / (1024 * 1024), 2)

def validate_pdf(path):
    """Check if file is a valid PDF.
    
    Args:
        path (str): Path to PDF file
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if not os.path.exists(path):
        return False, "File does not exist"
    
    if not path.lower().endswith('.pdf'):
        return False, "File is not a PDF"
    
    try:
        with open(path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)
            if page_count == 0:
                return False, "PDF has no pages"
        return True, f"Valid PDF with {page_count} pages"
    except Exception as e:
        return False, f"Error reading PDF: {str(e)}"

def safe_delete(path):
    """Delete file or folder with error handling.
    
    Args:
        path (str): Path to file or directory
    
    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True, f"Deleted file: {path}"
        elif os.path.isdir(path):
            shutil.rmtree(path)
            return True, f"Deleted directory: {path}"
        else:
            return False, "Path does not exist"
    except Exception as e:
        return False, f"Error deleting: {str(e)}"