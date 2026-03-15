# Teacher PDF Printer 📄

A Streamlit-based web application designed for teachers to convert multi-page PDF documents into custom layouts with multiple images per page. Perfect for creating handouts, study sheets, or condensed materials from existing PDFs.

## Architecture

Uses **Redis Queue for background processing** with three containerized services:

- **Web UI** (512MB, 0.5 CPU): Lightweight Streamlit interface - stays responsive
- **Redis** (256MB, 0.25 CPU): Job queue message broker
- **Worker** (1.5GB, 1.0 CPU): Background processor for heavy PDF operations

**Key Benefits:**
- Submit jobs and close browser - processing continues in background
- UI never freezes during PDF conversion or generation
- Manual refresh to check job status (no auto-polling)
- Controlled resource usage with one job at a time

## Features

### 🎯 Core Functionality
- **Background Processing**: Upload PDFs and let worker process while you do other things
- **PDF to Image Conversion**: Convert PDF pages to high-quality images with adaptive DPI (120-200 based on file size)
- **Flexible Layouts**: Arrange 1-9 images per output page with automatic grid layouts
- **Batch Processing**: Process images in manageable mini-batches of 4 images
- **Job Management**: Create, load, and manage multiple PDF processing jobs
- **Persistent Storage**: Auto-save selections and resume work at any time
- **Job Status Monitoring**: Manual refresh to check background job progress

### 📋 Job Management
- **Friendly Job Names**: Assign custom names to jobs for easy identification
- **Job History**: View all existing jobs with creation dates, DPI used, and progress tracking
- **Duplicate Prevention**: Automatic validation prevents duplicate job names
- **Delete Operations**: Remove individual jobs or delete all jobs at once
- **DPI Display**: See the actual DPI used for conversion in job info and batch interface

### 🖼️ Image Processing
- **Selective Exclusion**: Exclude specific images from the final PDF
- **Image Rotation**: Rotate mis-scanned pages 90° at a time (clockwise ↻ or counter-clockwise ↺)
- **Visual Preview**: Thumbnails display rotated orientation in real-time
- **Auto-Increment Page Numbers**: Smart page numbering with automatic increment as you work
- **Page Distribution**: Real-time sidebar showing how many images are assigned to each page
- **Validation**: Prevents generation if any page exceeds 9 images

### 📥 PDF Generation
- **Dynamic Layouts**:
  - 1 image: Full page
  - 2 images: Horizontal stack (auto-rotated to landscape)
  - 3-4 images: 2×2 grid
  - 5-6 images: 3×2 grid
  - 7-9 images: 3×3 grid
- **File Size Note**: Output PDFs are typically 2-3x the size of the original PDF. This is due to ReportLab's image embedding overhead when creating custom layouts with multiple images per page.
- **Download Management**: Download generated PDFs with friendly names
- **Regeneration**: Easily regenerate PDFs after making changes
- **Validation Warnings**: Alert when jobs are incomplete or pages are overloaded

### 🔍 Debug Features
- **Timestamped Logging**: UK format timestamps (DD/MM/YYYY HH:MM:SS) for:
  - New job creation
  - Job loading
  - PDF generation start and completion

## Installation

### Option 1: Docker (Recommended for Production)

See [DOCKER.md](DOCKER.md) for complete Docker setup instructions.

**Quick Start:**
```bash
docker-compose up --build -d
# Access at http://localhost:8507
```

### Option 2: Local Development

See [SETUP_REDIS.md](SETUP_REDIS.md) for local development setup with Redis.

**Quick Start:**
1. Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`
2. Install dependencies: `pip install -r requirements.txt`
3. Terminal 1 - Worker: `rq worker --url redis://localhost:6379 teacher_printer`
4. Terminal 2 - Streamlit: `streamlit run app.py --server.port=8507`

### Prerequisites
- Docker and Docker Compose (for containerized deployment)
- OR Python 3.8+ and Redis (for local development)
- pip (Python package manager)

## Usage

### Creating a New Job

1. **Start the Application**
   - Select "New Job" from the radio options

2. **Choose PDF Source**
   - **Option 1**: Upload a new PDF file
   - **Option 2**: Select from existing PDFs in the `printer_inputs` folder

3. **Assign a Name** (optional)
   - Enter a friendly name for easy identification
   - Leave blank to use the auto-generated job ID

4. **Create Job**
   - Click "Start New Job"
   - Job submitted to background worker for PDF conversion
   - You'll see "✅ PDF conversion job submitted!" message

5. **Monitor Progress**
   - Click "🔄 Refresh Job Status" in sidebar to check progress
   - Wait for "✅ Complete!" message
   - Click "View" button when conversion finishes

### Processing Images

1. **Navigate Batches**
   - Images are presented in mini-batches of 4
   - Use "Previous Batch" and "Next Batch" buttons to navigate
   - Selections are auto-saved when changing batches

2. **Assign Page Numbers**
   - Each image has a number selector
   - First image defaults to 1, subsequent images auto-increment
   - Modify any number as needed

3. **Rotate Images** (if needed)
   - Click **↻** to rotate 90° clockwise
   - Click **↺** to rotate 90° counter-clockwise
   - Rotation is saved automatically and shown in the thumbnail preview
   - Useful for correcting mis-scanned pages

4. **Exclude Images**
   - Check the "Exclude" box to skip an image
   - Excluded images won't appear in the final PDF

5. **Monitor Progress**
   - Sidebar shows page distribution in real-time
   - Warnings appear for pages with >9 images
   - Overall job progress displayed as percentage

### Generating PDFs

1. **Validate Your Selections**
   - Review the page distribution sidebar
   - Ensure no page exceeds 9 images

2. **Generate PDF**
   - Click "🎯 Generate PDF" button
   - Job submitted to background worker
   - Click "🔄 Refresh Job Status" to check progress

3. **Download**
   - When complete, click "📥 Download PDF" to save the file
   - Filename uses your friendly name (or job ID)

4. **Regenerate** (if needed)
   - Make changes to your selections
   - Click "🔄 Regenerate PDF" to rebuild
   - New job submitted to background worker

### Managing Jobs

#### Load Existing Job
1. Select "Continue Existing Job"
2. Choose from the list of existing jobs
3. View image count and progress
4. Click "Load Job"

#### Delete Jobs
- **Individual**: Click 🗑️ next to any job in the sidebar
- **Delete All**: Click "🗑️ Delete All Jobs" at top of Existing Jobs list

#### Reset to Job Selection
- Click "← Back to Job Selection" in the sidebar when viewing a job

## Directory Structure

```
teacworker.py                   # Background job processor (RQ worker)
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Three-service container orchestration
├── DOCKER.md                   # Docker deployment guide
├── SETUP_REDIS.md              # Redis setup and local development
├── Redis_Guide.md              # General Redis implementation guide
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── modules/                    # Application modules
│   ├── batch_manager.py       # Batch processing and selection management
│   ├── job_manager.py         # Job lifecycle and file operations
│   ├── page_builder.py        # PDF generation with dynamic layouts
│   ├── pdf_processor.py       # PDF to image conversion
│   └── utils.py               # Utility functions
├── printer_inputs/            # Temporary PDF uploads
├── printer_processes/         # Active job storage
│   └── job_YYYYMMDD_HHMMSS/  # Individual job folders
│       ├── images/            # Converted PDF pages (JPEG)
│       ├── thumbnails/        # Display thumbnails
│       ├── original.pdf       # Source PDF
│       ├── metadata.json      # Job metadata
│       └── selections.json    # Page assignments
└── printer_outputs/           # Generated PDFs
```

## Technical Details

### Key Dependencies
- **Streamlit**: Web application framework
- **Redis**: In-memory data store for job queue
- **RQ (Redis Queue)**: Background job processing
- **pdf2image**: PDF page conversion to JPEG images
- **Pillow (PIL)**: Image manipulation and rotation
- **reportlab**: PDF generation with custom layouts
- **PyPDF2**: PDF validation

### Session State Management
- `current_job_id`: Active job identifier
- `current_batch`: Current batch number (0-indexed)
- `last_page_number`: Tracks last assigned page for auto-increment
- `selections`: In-memory cache of image-to-page mappings
- `pending_jobs`: Tracks background jobs submitted to Redis

### Data Persistence
- **metadata.json**: Job information (name, creation date, source PDF, DPI used)
- **selections.json**: Image-to-page mappings with rotation data (`{"img_001": {"page": 1, "rotation": 90}}`)
- **Backward Compatible**: Old format without rotation still loads correctly
- **Auto-save**: Triggered on batch navigation and PDF generation

### Image Processing
- **Adaptive DPI Conversion**: Automatically adjusts DPI based on PDF file size to balance quality with memory constraints:
  - **< 20 MB**: 200 DPI (high quality)
  - **20-50 MB**: 175 DPI (good quality)
  - **50-100 MB**: 150 DPI (acceptable quality)
  - **> 100 MB**: 120 DPI (readable, memory-safe)
- **DPI Persistence**: Used DPI is saved to job metadata and displayed throughout the UI
- **Format**: JPEG images with quality=85 compression
- **Thumbnails**: Max 800px for UI display
- **Rotation**: 2-image layouts rotated -90° to landscape orientation
- **Sorting**: Numerical sorting ensures consistent image order
- **Memory Optimization**: Page-by-page processing with explicit garbage collection

## Tips & Best Practices

1. **Background Processing**: You can close the browser after submitting jobs - the worker keeps processing
2. **Refresh Status**: Click "🔄 Refresh Job Status" manually to check on background jobs
3. **Batch Size**: Process 4 images at a time to reduce cognitive load
4. **Naming**: Use descriptive friendly names for easy job identification
5. **Validation**: Review the page distribution sidebar before generating
6. **Auto-increment**: Let the first image set the page, others follow automatically
7. **Exclusion**: Use page 0 (exclude) for cover pages or unwanted content
8. **Rotation**: Fix mis-scanned pages by rotating before assigning to output pages
9. **Regeneration**: Safe to regenerate PDFs multiple times - old versions are replaced

## Troubleshooting

### Job stuck in "Processing..."
- Check worker logs: `docker-compose logs -f teacher-printer-worker`
- Restart worker: `docker-compose restart teacher-printer-worker`

### Redis connection failed
- Ensure Redis container is running: `docker ps | grep redis`
- Test connection: `docker exec teacher-printer-redis redis-cli ping`

### Images appear small in 2-image layout
- The app automatically rotates 2-image pages to landscape orientation
- Images stack vertically in portrait orientation

### Page distribution warnings
- Maximum 9 images per page
- Reduce images on overloaded pages before generating

### Job not found
- Ensure job exists in `printer_processes` directory
- Check for accidental deletion

### PDF generation fails
- Verify all image files exist in job's `images/` folder
- Check worker logs for detailed error messages with timestamps
- Clear stuck jobs: `docker exec teacher-printer-redis redis-cli FLUSHDB`

## Debug Mode

The application logs key events with UK timestamps to help monitor background processing:

**Web UI logs** (Streamlit console):
```
[26/12/2025 14:30:45] NEW JOB CREATED: My Worksheet (ID: job_20251226_143045)
[26/12/2025 14:32:10] JOB LOADED: My Worksheet (ID: job_20251226_143045)
```

**Worker logs** (`docker-compose logs -f teacher-printer-worker`):
```
[26/12/2025 14:30:50] WORKER: PDF conversion started for My Worksheet
[26/12/2025 14:31:15] WORKER: PDF conversion completed for My Worksheet - 24 images
[26/12/2025 14:35:22] WORKER: PDF generation started for My Worksheet
[26/12/2025 14:35:28] WORKER: PDF generation completed for My Worksheet
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/)
- [pdf2image](https://github.com/Belval/pdf2image)
- [ReportLab](https://www.reportlab.com/)
- [Pillow](https://python-pillow.org/)

---

**Author**: Simon  
**Version**: 1.3  
**Last Updated**: March 2026
