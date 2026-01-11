# Purpose: shared helped functions.

import os
import shutil
from pathlib import Path
import PyPDF2
import zipfile

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

def validate_zip(path):
    """Basic validation for a ZIP file.
    
    Args:
        path (str): Path to ZIP file
    
    Returns:
        tuple: (bool, str) - (is_valid, message)
    """
    if not os.path.exists(path):
        return False, "File does not exist"
    if not path.lower().endswith('.zip'):
        return False, "File is not a ZIP"
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            bad = zf.testzip()
            if bad:
                return False, f"Corrupt ZIP entry: {bad}"
        return True, "Valid ZIP"
    except Exception as e:
        return False, f"Error reading ZIP: {str(e)}"

def list_pdfs_in_zip(zip_path):
    """List PDF member names inside a ZIP (excluding directories).
    
    Args:
        zip_path (str): Path to ZIP file
    
    Returns:
        list[str]: Member paths (as stored in the ZIP) that end with .pdf
    """
    out = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if name.lower().endswith('.pdf'):
                out.append(name)
    return out

def safe_extract_selected(zip_path, dest_dir, members):
    """Extract selected members from ZIP to dest_dir safely (no path traversal).
    Streams to disk to avoid memory spikes.
    
    Args:
        zip_path (str): Path to ZIP file
        dest_dir (str): Destination directory
        members (list[str]): Member names to extract
    """
    os.makedirs(dest_dir, exist_ok=True)
    dest_root = os.path.abspath(dest_dir)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in members:
            target = os.path.abspath(os.path.join(dest_root, member))
            # Prevent path traversal
            if not target.startswith(dest_root + os.sep):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(member, 'r') as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)  # 1MB chunks

def write_uploaded_file_chunked(uploaded_file, dest_path, chunk_size=4 * 1024 * 1024):
    """Write a Streamlit UploadedFile to disk in chunks to avoid high memory use.
    
    Args:
        uploaded_file: Streamlit UploadedFile
        dest_path (str): Destination file path
        chunk_size (int): Chunk size in bytes (default 4MB)
    
    Returns:
        str: Path to written file
    """
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    with open(dest_path, 'wb') as f:
        while True:
            chunk = uploaded_file.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
    return dest_path

def get_pdf_title(pdf_path):
    """Best-effort PDF title fetch. Falls back to filename if missing."""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            meta = getattr(pdf_reader, 'metadata', None) or getattr(pdf_reader, 'documentInfo', None)
            if meta:
                title = getattr(meta, 'title', None) or meta.get('/Title')
                if isinstance(title, str) and title.strip():
                    return title.strip()
    except Exception:
        pass
    return os.path.basename(pdf_path)

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