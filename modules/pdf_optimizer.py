# Purpose: Optimize PDF file size using PyMuPDF (fitz) with two modes:
# 1. Safe Mode: Structural optimization only (10-30% reduction, zero quality loss)
# 2. Aggressive Mode: Structural + image downsampling (30-50% reduction, configurable)

import os
import shutil

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


def optimize_pdf_safe(input_path, output_path):
    """
    Safe mode: Structural optimization only.
    
    Uses PyMuPDF's save options to:
    - Remove unused objects (garbage collection)
    - Compress streams (deflate)
    - Clean/optimize PDF structure
    - Remove whitespace (pretty=False)
    
    Expected result: 10-30% file size reduction with ZERO quality loss.
    
    Args:
        input_path: Path to input PDF
        output_path: Path for optimized output
    
    Returns:
        tuple: (success: bool, reduction_percent: float)
    """
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping safe optimization")
        return False, 0.0
    
    original_size = os.path.getsize(input_path)
    
    try:
        # Open the PDF
        doc = pymupdf.open(input_path)
        
        # Save with structural optimization only
        doc.save(
            output_path,
            garbage=4,        # Maximize cleaning of unused objects
            deflate=True,     # Use deflate lossless compression
            clean=True,       # Clean/optimize PDF internal structure
            pretty=False      # Compact output, remove whitespace
        )
        
        doc.close()
        
        # Check if optimization helped
        if os.path.exists(output_path):
            optimized_size = os.path.getsize(output_path)
            
            if optimized_size >= original_size:
                # Optimization made it larger or same size
                shutil.copy2(input_path, output_path)
                return False, 0.0
            
            reduction = (1 - optimized_size / original_size) * 100
            return True, reduction
        
        return False, 0.0
        
    except Exception as e:
        print(f"Safe optimization failed: {e}")
        # Copy original as fallback
        if not os.path.exists(output_path):
            shutil.copy2(input_path, output_path)
        return False, 0.0


def optimize_pdf_aggressive(input_path, output_path, dpi_threshold=200, dpi_target=150, quality=80):
    """
    Aggressive mode: Structural optimization + image downsampling.
    
    First rewrites images that exceed dpi_threshold, downsampling them to dpi_target
    with specified JPEG quality, then applies structural optimization.
    
    Expected result: 30-50% file size reduction with configurable quality trade-off.
    
    Args:
        input_path: Path to input PDF
        output_path: Path for optimized output
        dpi_threshold: Only process images above this DPI (default 200)
        dpi_target: Downsample images to this DPI (default 150)
        quality: JPEG quality for recompressed images (default 80)
    
    Returns:
        tuple: (success: bool, reduction_percent: float)
    """
    if not PYMUPDF_AVAILABLE:
        print("PyMuPDF not available, skipping aggressive optimization")
        return False, 0.0
    
    original_size = os.path.getsize(input_path)
    
    try:
        # Open the PDF
        doc = pymupdf.open(input_path)
        
        # Rewrite images that exceed the threshold
        doc.rewrite_images(
            dpi_threshold=dpi_threshold,  # Only process high-DPI images
            dpi_target=dpi_target,        # Downsample to target DPI
            quality=quality,              # JPEG quality
            lossy=True,                   # Include lossy (JPEG) images
            color=True                    # Include color images
        )
        
        # Save with structural optimization
        doc.save(
            output_path,
            garbage=4,        # Maximize cleaning of unused objects
            deflate=True,     # Use deflate lossless compression
            clean=True,       # Clean/optimize PDF internal structure
            pretty=False      # Compact output, remove whitespace
        )
        
        doc.close()
        
        # Check if optimization helped
        if os.path.exists(output_path):
            optimized_size = os.path.getsize(output_path)
            
            if optimized_size >= original_size:
                # Optimization made it larger or same size
                shutil.copy2(input_path, output_path)
                return False, 0.0
            
            reduction = (1 - optimized_size / original_size) * 100
            return True, reduction
        
        return False, 0.0
        
    except Exception as e:
        print(f"Aggressive optimization failed: {e}")
        # Copy original as fallback
        if not os.path.exists(output_path):
            shutil.copy2(input_path, output_path)
        return False, 0.0


def check_pymupdf_available():
    """Check if PyMuPDF is installed and available."""
    return PYMUPDF_AVAILABLE
