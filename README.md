# Teacher PDF Printer 📄

A Streamlit-based web application designed for teachers to convert multi-page PDF documents into custom layouts with multiple images per page. Perfect for creating handouts, study sheets, or condensed materials from existing PDFs.

## Features

### 🎯 Core Functionality
- **PDF to Image Conversion**: Convert PDF pages to high-quality images (200 DPI)
- **Flexible Layouts**: Arrange 1-9 images per output page with automatic grid layouts
- **Batch Processing**: Process images in manageable mini-batches of 4 images
- **Job Management**: Create, load, and manage multiple PDF processing jobs
- **Persistent Storage**: Auto-save selections and resume work at any time

### 📋 Job Management
- **Friendly Job Names**: Assign custom names to jobs for easy identification
- **Job History**: View all existing jobs with creation dates and progress tracking
- **Duplicate Prevention**: Automatic validation prevents duplicate job names
- **Delete Operations**: Remove individual jobs or delete all jobs at once

### 🖼️ Image Processing
- **Selective Exclusion**: Exclude specific images from the final PDF
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
- **Download Management**: Download generated PDFs with friendly names
- **Regeneration**: Easily regenerate PDFs after making changes
- **Validation Warnings**: Alert when jobs are incomplete or pages are overloaded

### 🔍 Debug Features
- **Timestamped Logging**: UK format timestamps (DD/MM/YYYY HH:MM:SS) for:
  - New job creation
  - Job loading
  - PDF generation start and completion

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/teacher_printer.git
   cd teacher_printer
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   
   # On Linux/Mac:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Access the app**
   - The application will automatically open in your default browser
   - Default URL: `http://localhost:8501`

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
   - PDF will be automatically converted to images

### Processing Images

1. **Navigate Batches**
   - Images are presented in mini-batches of 4
   - Use "Previous Batch" and "Next Batch" buttons to navigate
   - Selections are auto-saved when changing batches

2. **Assign Page Numbers**
   - Each image has a number selector
   - First image defaults to 1, subsequent images auto-increment
   - Modify any number as needed

3. **Exclude Images**
   - Check the "Exclude" box to skip an image
   - Excluded images won't appear in the final PDF

4. **Monitor Progress**
   - Sidebar shows page distribution in real-time
   - Warnings appear for pages with >9 images
   - Overall job progress displayed as percentage

### Generating PDFs

1. **Validate Your Selections**
   - Review the page distribution sidebar
   - Ensure no page exceeds 9 images

2. **Generate PDF**
   - Click "🎯 Generate PDF" button
   - Wait for processing (progress spinner will show)

3. **Download**
   - Click "📥 Download PDF" to save the file
   - Filename uses your friendly name (or job ID)

4. **Regenerate** (if needed)
   - Make changes to your selections
   - Click "🔄 Regenerate PDF" to rebuild

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
teacher_printer/
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
│       ├── images/            # Converted PDF pages (PNG)
│       ├── thumbnails/        # Display thumbnails
│       ├── original.pdf       # Source PDF
│       ├── metadata.json      # Job metadata
│       └── selections.json    # Page assignments
└── printer_outputs/           # Generated PDFs
```

## Technical Details

### Key Dependencies
- **Streamlit**: Web application framework
- **pdf2image**: PDF page conversion to PNG images
- **Pillow (PIL)**: Image manipulation and rotation
- **reportlab**: PDF generation with custom layouts
- **PyPDF2**: PDF validation

### Session State Management
- `current_job_id`: Active job identifier
- `current_batch`: Current batch number (0-indexed)
- `last_page_number`: Tracks last assigned page for auto-increment
- `selections`: In-memory cache of image-to-page mappings

### Data Persistence
- **metadata.json**: Job information (name, creation date, source PDF)
- **selections.json**: Image-to-page number mappings
- **Auto-save**: Triggered on batch navigation and PDF generation

### Image Processing
- **Conversion**: 200 DPI PNG images
- **Thumbnails**: Max 800px for UI display
- **Rotation**: 2-image layouts rotated -90° to landscape orientation
- **Sorting**: Numerical sorting ensures consistent image order

## Tips & Best Practices

1. **Batch Size**: Process 4 images at a time to reduce cognitive load
2. **Naming**: Use descriptive friendly names for easy job identification
3. **Validation**: Review the page distribution sidebar before generating
4. **Auto-increment**: Let the first image set the page, others follow automatically
5. **Exclusion**: Use page 0 (exclude) for cover pages or unwanted content
6. **Regeneration**: Safe to regenerate PDFs multiple times - old versions are replaced

## Troubleshooting

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
- Check console for detailed error messages with timestamps

## Debug Mode

The application logs key events to the console with UK timestamps:

```
[26/12/2025 14:30:45] NEW JOB CREATED: My Worksheet (ID: job_20251226_143045)
[26/12/2025 14:32:10] JOB LOADED: My Worksheet (ID: job_20251226_143045)
[26/12/2025 14:35:22] PDF GENERATION STARTED: My Worksheet (ID: job_20251226_143045)
[26/12/2025 14:35:28] PDF GENERATION COMPLETED: My Worksheet - 3 pages
```

Monitor the terminal/console running Streamlit for these logs.

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
**Version**: 1.0.0  
**Last Updated**: December 2025
