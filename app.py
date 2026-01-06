# Purpose: orchestrate the UI and coordinate between modules.

import streamlit as st
import os
from PIL import Image
from redis import Redis
from rq import Queue
from rq.job import Job
from modules import utils, job_manager, pdf_processor, batch_manager, page_builder
import sys
import os

# Add current directory to path for worker import
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import worker  # Import worker module for job functions

# Redis connection
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

@st.cache_resource
def get_redis_connection():
    """Get Redis connection with caching."""
    try:
        redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
        redis_conn.ping()
        return redis_conn
    except Exception as e:
        st.error(f"⚠️ Cannot connect to Redis at {REDIS_HOST}:{REDIS_PORT}. Make sure Redis is running.")
        st.info("To start Redis locally: `docker run -d -p 6379:6379 redis:7-alpine`")
        return None

def get_queue():
    """Get RQ queue instance."""
    redis_conn = get_redis_connection()
    if redis_conn:
        return Queue('default', connection=redis_conn)
    return None

def get_current_selections(existing_selections):
    """Merge current widget values with existing selections from disk, maintaining order.

    Handles three cases per image key:
    - Excluded via checkbox: saved as 0
    - Assigned to a page: saved as that page number (>0)
    - Not yet processed in UI: no entry created
    """
    merged = {}

    # 1) Start with what's already saved, letting current widget states override
    for img_key, saved_value in existing_selections.items():
        exclude_key = f"exclude_{img_key}"
        if st.session_state.get(exclude_key, False):
            merged[img_key] = 0
        else:
            widget_key = f"page_{img_key}"
            merged[img_key] = st.session_state.get(widget_key, saved_value)

    # 2) Collect new images seen only in the current UI state
    page_keys = []
    for key in st.session_state.keys():
        if key.startswith("page_") and not key.startswith("page_num_"):
            img_key = key.replace("page_", "")
            if img_key not in merged:
                page_keys.append(img_key)

    # 3) Also collect images that only have an exclude checkbox (no page widget)
    exclude_only_keys = []
    for key in st.session_state.keys():
        if key.startswith("exclude_") and st.session_state.get(key, False):
            img_key = key.replace("exclude_", "")
            if img_key not in merged and f"page_{img_key}" not in st.session_state:
                exclude_only_keys.append(img_key)

    def sort_img_keys(keys):
        try:
            return sorted(keys, key=lambda x: int(x.split('_')[1]))
        except Exception:
            return sorted(keys)

    # 4) Add page-keyed images (respect exclude if checked)
    for img_key in sort_img_keys(page_keys):
        widget_key = f"page_{img_key}"
        exclude_key = f"exclude_{img_key}"
        if st.session_state.get(exclude_key, False):
            merged[img_key] = 0
        else:
            merged[img_key] = st.session_state.get(widget_key, 1)

    # 5) Add exclude-only images as excluded
    for img_key in sort_img_keys(exclude_only_keys):
        merged[img_key] = 0

    return merged

def get_page_counts(selections_dict):
    """Count images per page number.
    
    Args:
        selections_dict (dict): Image to page mappings
    
    Returns:
        dict: {page_num: image_count} sorted by page number (excludes page 0)
    """
    page_counts = {}
    for img_key, page_num in selections_dict.items():
        if page_num == 0:  # Skip excluded images
            continue
        if page_num not in page_counts:
            page_counts[page_num] = 0
        page_counts[page_num] += 1
    return dict(sorted(page_counts.items()))

def check_duplicate_friendly_name(friendly_name):
    """Check if a friendly name already exists in existing jobs.
    
    Args:
        friendly_name (str): The friendly name to check
    
    Returns:
        bool: True if name already exists, False otherwise
    """
    if not friendly_name or not friendly_name.strip():
        return False
    
    jobs = job_manager.list_jobs()
    for job in jobs:
        info = job_manager.get_job_info(job)
        if info and info.get('friendly_name') == friendly_name.strip():
            return True
    return False

def main():
    """Main entry point for Streamlit app."""
    st.set_page_config(
        page_title="Teacher PDF Printer",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 Teacher PDF Printer")
    
    # Ensure directories exist
    utils.ensure_directories()
    
    # Initialize session state
    if 'current_job_id' not in st.session_state:
        st.session_state.current_job_id = None
    if 'current_batch' not in st.session_state:
        st.session_state.current_batch = 0
    if 'selections' not in st.session_state:
        st.session_state.selections = {}
    
    # Sidebar for job management
    render_job_manager()
    
    # Main content
    if st.session_state.current_job_id is None:
        render_job_selector()
    else:
        render_batch_interface(st.session_state.current_job_id, st.session_state.current_batch)
        render_pdf_generator()

def render_job_selector():
    """UI for selecting new or existing job."""
    st.header("Select or Create Job")
    
    job_type = st.radio("Choose option:", ["New Job", "Continue Existing Job"])
    
    if job_type == "New Job":
        st.subheader("Create New Job")
        job_name = st.text_input("Job name (optional)")
        
        # Option 1: Upload PDF
        st.write("**Option 1: Upload a new PDF**")
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        
        # Option 2: Select from printer_inputs folder
        printer_inputs_dir = 'printer_inputs'
        local_pdfs = []
        if os.path.exists(printer_inputs_dir):
            local_pdfs = [f for f in os.listdir(printer_inputs_dir) if f.endswith('.pdf')]
        
        if local_pdfs:
            st.write("**Option 2: Select from existing PDFs**")
            selected_pdf = st.selectbox("PDFs in printer_inputs folder", [''] + local_pdfs)
        else:
            selected_pdf = None
        
        if st.button("Start New Job"):
            pdf_source = None
            
            # Check for duplicate friendly name
            if job_name.strip():
                if check_duplicate_friendly_name(job_name):
                    st.error(f"❌ A job with the name '{job_name}' already exists. Please use a different name.")
                    st.stop()
            
            if uploaded_file:
                # Save uploaded file temporarily in printer_inputs
                temp_path = os.path.join('printer_inputs', f"temp_{uploaded_file.name}")
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.read())
                pdf_source = temp_path
            elif selected_pdf:
                # Use PDF from printer_inputs folder
                pdf_source = os.path.join('printer_inputs', selected_pdf)
            
            if pdf_source:
                # Validate PDF
                is_valid, message = utils.validate_pdf(pdf_source)
                if is_valid:
                    # Create job
                    job_id, result = job_manager.create_job(pdf_source, friendly_name=job_name)
                    if job_id:
                        display_name = job_name.strip() if job_name and job_name.strip() else job_id
                        st.success(f"Job created: {display_name}")
                        
                        # Submit PDF conversion to background queue
                        queue = get_queue()
                        if queue:
                            paths = job_manager.get_job_paths(job_id)
                            rq_job = queue.enqueue(
                                worker.process_pdf_to_images,
                                job_id,
                                paths['pdf'],
                                200,
                                job_timeout='10m'
                            )
                            
                            # Store RQ job ID in session state
                            if 'pending_jobs' not in st.session_state:
                                st.session_state.pending_jobs = {}
                            st.session_state.pending_jobs[job_id] = {
                                'rq_job_id': rq_job.id,
                                'type': 'pdf_conversion',
                                'display_name': display_name
                            }
                            
                            st.success("✅ PDF conversion job submitted! Processing in background...")
                            st.info("📊 Check job status in the sidebar. The page will update automatically when complete.")
                            st.session_state.current_job_id = job_id
                            st.session_state.current_batch = 0
                            st.session_state.last_page_number = 1
                            st.rerun()
                        else:
                            st.error("❌ Cannot submit job - Redis not available")
                    else:
                        st.error(result)
                else:
                    st.error(message)
            else:
                st.warning("Please upload or select a PDF")
    
    else:
        st.subheader("Continue Existing Job")
        jobs = job_manager.list_jobs()
        
        if jobs:
            job_infos = {job: job_manager.get_job_info(job) for job in jobs}
            def job_label(job_id):
                info = job_infos.get(job_id) or {}
                name = info.get('friendly_name') or job_id
                created = info.get('created')
                return f"{name} ({created})" if created else name
            selected_job = st.selectbox("Select job:", jobs, format_func=job_label)
            
            if selected_job:
                info = job_infos.get(selected_job) or job_manager.get_job_info(selected_job)
                st.write(f"**Images:** {info['image_count']}")
                if info.get('dpi'):
                    st.write(f"**DPI:** {info['dpi']}")
                st.write(f"**Progress:** {info['progress_percent']}%")
                st.progress(info['progress_percent'] / 100)
                
                if st.button("Load Job"):
                    st.session_state.current_job_id = selected_job
                    st.session_state.current_batch = 0
                    st.session_state.selections = batch_manager.load_selections(selected_job)
                    # Reset last_page_number - will be recalculated from selections
                    if 'last_page_number' in st.session_state:
                        del st.session_state.last_page_number
                    
                    # Debug: Log job load
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                    job_display = info.get('friendly_name') or selected_job
                    print(f"[{timestamp}] JOB LOADED: {job_display} (ID: {selected_job})")
                    
                    st.rerun()
        else:
            st.info("No existing jobs found")

def render_batch_interface(job_id, batch_num):
    """Display images with page number selectors."""
    info = job_manager.get_job_info(job_id) or {}
    display_name = info.get('friendly_name') or job_id
    dpi = info.get('dpi')
    if dpi:
        st.header(f"Job: {display_name} • {dpi} DPI")
    else:
        st.header(f"Job: {display_name}")
    if info.get('friendly_name'):
        st.caption(f"ID: {job_id}")
    
    # Get batch info - use mini-batches of 4 images
    total_images = pdf_processor.get_image_count(job_id)
    
    # Check if images are still being processed
    if total_images == 0:
        # Check if there's a pending conversion job
        if 'pending_jobs' in st.session_state and job_id in st.session_state.pending_jobs:
            st.info("⏳ PDF is being converted to images in the background. Please wait...")
            st.caption("Check the sidebar for job status. The page will update automatically when complete.")
            return
        else:
            st.warning("⚠️ No images found for this job. The conversion may have failed or not started yet.")
            if st.button("🔄 Start PDF Conversion"):
                paths = job_manager.get_job_paths(job_id)
                queue = get_queue()
                if queue and os.path.exists(paths['pdf']):
                    rq_job = queue.enqueue(
                        worker.process_pdf_to_images,
                        job_id,
                        paths['pdf'],
                        200,
                        job_timeout='10m'
                    )
                    
                    if 'pending_jobs' not in st.session_state:
                        st.session_state.pending_jobs = {}
                    st.session_state.pending_jobs[job_id] = {
                        'rq_job_id': rq_job.id,
                        'type': 'pdf_conversion',
                        'display_name': display_name
                    }
                    st.success("✅ PDF conversion job submitted!")
                    st.rerun()
            return
    batches = batch_manager.create_batches(total_images, batch_size=4)
    total_batches = len(batches)
    
    if batch_num >= total_batches:
        batch_num = total_batches - 1
        st.session_state.current_batch = batch_num
    
    # Load existing selections early
    all_selections = batch_manager.load_selections(job_id)
    
    # Initialize last_page_number in session state if not present
    if 'last_page_number' not in st.session_state:
        # Start with 1, but if there are existing selections, use the max page number
        if all_selections:
            valid_pages = [p for p in all_selections.values() if p > 0]
            st.session_state.last_page_number = max(valid_pages) if valid_pages else 1
        else:
            st.session_state.last_page_number = 1
    
    # Get status
    status = batch_manager.get_batch_selection_status(job_id, batch_num, total_batches, batch_size=4)
    
    st.write(f"**Mini-Batch {status['batch_num']} of {status['total_batches']}** (4 images per batch)")
    st.write(f"Overall Progress: {status['overall_complete']}/{status['overall_total']} ({status['overall_percent']}%)")
    st.progress(status['overall_percent'] / 100)
    
    # Navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Previous Batch", disabled=(batch_num == 0)):
            # Auto-save with current widget values before navigating
            existing_selections = batch_manager.load_selections(job_id)
            current_selections = get_current_selections(existing_selections)
            batch_manager.save_selections(job_id, current_selections)
            st.session_state.current_batch -= 1
            st.rerun()
    with col3:
        if st.button("Next Batch →", disabled=(batch_num >= total_batches - 1)):
            # Auto-save with current widget values before navigating
            existing_selections = batch_manager.load_selections(job_id)
            current_selections = get_current_selections(existing_selections)
            batch_manager.save_selections(job_id, current_selections)
            st.session_state.current_batch += 1
            st.rerun()
    
    # Get batch images
    batch_start, batch_end = batches[batch_num]
    batch_data = batch_manager.get_batch_images(job_id, batch_start, batch_end)
    
    # Display page distribution in sidebar
    with st.sidebar:
        st.subheader("📊 Page Distribution")
        page_counts = get_page_counts(all_selections)
        if page_counts:
            # Check for pages exceeding 9 images
            invalid_pages = [page for page, count in page_counts.items() if count > 9]
            if invalid_pages:
                st.warning(f"⚠️ Pages over limit: {', '.join([f'Page {p} ({page_counts[p]} images)' for p in invalid_pages])}")
            
            for page_num, count in page_counts.items():
                if count > 9:
                    st.metric(f"Page {page_num} ❌", f"{count} images", delta=f"{count - 9} over limit")
                else:
                    st.metric(f"Page {page_num}", f"{count} images")
        else:
            st.info("No pages assigned yet")
    
    # Display images in single row
    st.subheader("Assign Page Numbers")
    
    thumbnails = batch_data['thumbnails']
    image_numbers = batch_data['image_numbers']
    
    # Display all images in this mini-batch in one row
    cols = st.columns(len(thumbnails))
    
    for idx, col in enumerate(cols):
        with col:
            img_num = image_numbers[idx]
            img_key = f"img_{img_num:03d}"
            
            # Display thumbnail
            try:
                thumb_img = Image.open(thumbnails[idx])
                st.image(thumb_img, caption=f"Image {img_num}", width="stretch")
            except Exception as e:
                st.error(f"Error loading image {img_num}: {str(e)}")
            
            # Page number input with auto-increment from session state
            if img_key in all_selections:
                # Use saved value
                default_value = all_selections[img_key]
            else:
                # Use last page number from session state
                default_value = st.session_state.last_page_number
            
            # Check if currently excluded (page 0)
            is_excluded = all_selections.get(img_key, default_value) == 0
            
            # Exclude checkbox
            exclude = st.checkbox(
                "Exclude",
                value=is_excluded,
                key=f"exclude_{img_key}"
            )
            
            if exclude:
                # If excluded, set page to 0
                all_selections[img_key] = 0
                st.caption("Excluded from PDF")
            else:
                # Show page number input if not excluded
                page_num = st.number_input(
                    f"Page #",
                    min_value=1,
                    value=default_value if default_value > 0 else st.session_state.last_page_number,
                    key=f"page_{img_key}"
                )
                
                # Update selections and session state
                all_selections[img_key] = page_num
                st.session_state.last_page_number = page_num
    
    # Save button
    if st.button("💾 Save Batch", type="primary"):
        # Collect current widget values and save
        current_selections = get_current_selections(all_selections)
        success, msg = batch_manager.save_selections(job_id, current_selections)
        if success:
            st.success(msg)
            st.rerun()  # Rerun to update sidebar metrics
        else:
            st.error(msg)

def render_pdf_generator():
    """Button to generate output PDF."""
    st.divider()
    st.header("Generate Output PDF")
    
    job_id = st.session_state.current_job_id
    info = job_manager.get_job_info(job_id)
    paths = job_manager.get_job_paths(job_id)
    
    # Show progress warning if incomplete
    if info['progress_percent'] < 100:
        st.warning(f"⚠️ Job is {info['progress_percent']}% complete. Unselected images will be skipped.")
    
    # Check if PDF already exists
    pdf_exists = os.path.exists(paths['output'])
    
    if pdf_exists:
        # PDF exists - show regenerate and download side by side
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Regenerate PDF", type="secondary", use_container_width=True):
                # Auto-save current selections before generating
                existing_selections = batch_manager.load_selections(job_id)
                current_selections = get_current_selections(existing_selections)
                batch_manager.save_selections(job_id, current_selections)
                
                # Validate page counts (max 9 images per page)
                page_counts = get_page_counts(current_selections)
                invalid_pages = [page for page, count in page_counts.items() if count > 9]
                
                if invalid_pages:
                    error_msg = f"❌ Pages with too many images: {', '.join([f'Page {p} ({page_counts[p]} images)' for p in invalid_pages])}. Maximum 9 images per page."
                    st.error(error_msg)
                else:
                    # Submit PDF generation to background queue
                    queue = get_queue()
                    if queue:
                        rq_job = queue.enqueue(
                            worker.generate_output_pdf,
                            job_id,
                            current_selections,
                            paths['output'],
                            job_timeout='10m'
                        )
                        
                        # Store RQ job ID in session state
                        if 'pending_jobs' not in st.session_state:
                            st.session_state.pending_jobs = {}
                        st.session_state.pending_jobs[f"{job_id}_pdf"] = {
                            'rq_job_id': rq_job.id,
                            'type': 'pdf_generation',
                            'display_name': info.get('friendly_name') or job_id
                        }
                        
                        st.success("✅ PDF regeneration submitted! Processing in background...")
                        st.rerun()
                    else:
                        st.error("❌ Cannot submit job - Redis not available")
        
        with col2:
            # Download button
            with open(paths['output'], 'rb') as f:
                pdf_data = f.read()
                filename = f"{info.get('friendly_name') or job_id}.pdf"
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_data,
                    file_name=filename,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
    
    else:
        # No PDF exists - show generate button
        if st.button("🎯 Generate PDF", type="primary"):
            # Auto-save current selections before generating
            existing_selections = batch_manager.load_selections(job_id)
            current_selections = get_current_selections(existing_selections)
            batch_manager.save_selections(job_id, current_selections)
            
            # Validate page counts (max 9 images per page)
            page_counts = get_page_counts(current_selections)
            invalid_pages = [page for page, count in page_counts.items() if count > 9]
            
            if invalid_pages:
                error_msg = f"❌ Pages with too many images: {', '.join([f'Page {p} ({page_counts[p]} images)' for p in invalid_pages])}. Maximum 9 images per page."
                st.error(error_msg)
            else:
                # Submit PDF generation to background queue
                queue = get_queue()
                if queue:
                    rq_job = queue.enqueue(
                        worker.generate_output_pdf,
                        job_id,
                        current_selections,
                        paths['output'],
                        job_timeout='10m'
                    )
                    
                    # Store RQ job ID in session state
                    if 'pending_jobs' not in st.session_state:
                        st.session_state.pending_jobs = {}
                    st.session_state.pending_jobs[f"{job_id}_pdf"] = {
                        'rq_job_id': rq_job.id,
                        'type': 'pdf_generation',
                        'display_name': info.get('friendly_name') or job_id
                    }
                    
                    st.success("✅ PDF generation submitted! Processing in background...")
                    st.rerun()
                else:
                    st.error("❌ Cannot submit job - Redis not available")



def render_job_manager():
    """Sidebar UI for managing jobs."""
    with st.sidebar:
        st.header("Job Management")
        
        # Display pending background jobs
        # Display pending background jobs
        if 'pending_jobs' in st.session_state and st.session_state.pending_jobs:
            st.subheader("🔄 Background Jobs")
            
            # Manual refresh button
            if st.button("🔄 Refresh Job Status", use_container_width=True):
                st.rerun()
            
            redis_conn = get_redis_connection()
            
            if redis_conn:
                completed_jobs = []
                
                for job_key, job_info in st.session_state.pending_jobs.items():
                    try:
                        rq_job = Job.fetch(job_info['rq_job_id'], connection=redis_conn)
                        status = rq_job.get_status()
                        
                        if status == 'finished':
                            st.success(f"✅ {job_info['display_name']} - {job_info['type']} complete!")
                            completed_jobs.append(job_key)
                            
                            # Button to view completed job
                            if job_info['type'] == 'pdf_conversion':
                                if st.button(f"View {job_info['display_name']}", key=f"view_{job_key}"):
                                    st.rerun()
                        
                        elif status == 'failed':
                            st.error(f"❌ {job_info['display_name']} - {job_info['type']} failed")
                            completed_jobs.append(job_key)
                            if rq_job.exc_info:
                                with st.expander("Error details"):
                                    st.code(rq_job.exc_info)
                        
                        elif status in ['queued', 'started']:
                            # Show progress
                            meta = rq_job.meta
                            progress = meta.get('progress', 0)
                            status_msg = meta.get('status', 'Processing...')
                            
                            st.info(f"⏳ {job_info['display_name']} - {job_info['type']}")
                            st.caption(status_msg)
                            if progress > 0:
                                st.progress(progress / 100)
                    
                    except Exception as e:
                        st.warning(f"⚠️ Cannot check job status: {str(e)}")
                        completed_jobs.append(job_key)
                
                # Remove completed jobs from pending list
                for job_key in completed_jobs:
                    del st.session_state.pending_jobs[job_key]
            
            st.divider()
        
        jobs = job_manager.list_jobs()
        
        if jobs:
            with st.expander("Existing Jobs", expanded=False):
                # Delete all button
                if st.button("🗑️ Delete All Jobs", type="secondary", use_container_width=True):
                    success, msg = job_manager.delete_all_jobs()
                    if success:
                        # Clear current job if it was deleted
                        if st.session_state.current_job_id:
                            st.session_state.current_job_id = None
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                
                st.divider()
                
                for job in jobs[:10]:  # Show last 10
                    info = job_manager.get_job_info(job)
                    if not info:
                        continue
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        display_name = info.get('friendly_name') or job
                        st.write(f"**{display_name}**")
                        st.caption(f"{job} • {info['progress_percent']}% complete")
                    with col2:
                        if st.button("🗑️", key=f"del_{job}"):
                            success, msg = job_manager.delete_job(job)
                            if success:
                                # Clear current job if this was the active one
                                if st.session_state.current_job_id == job:
                                    st.session_state.current_job_id = None
                                st.success("Deleted!")
                                st.rerun()
                            else:
                                st.error(msg)
        
        # Reset button
        if st.session_state.current_job_id:
            if st.button("← Back to Job Selection"):
                st.session_state.current_job_id = None
                st.session_state.current_batch = 0
                st.rerun()

if __name__ == "__main__":
    main()