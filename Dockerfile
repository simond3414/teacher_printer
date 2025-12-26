# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for pdf2image
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY modules/ modules/

# Create directories for volumes
RUN mkdir -p printer_inputs printer_outputs printer_processes

# Expose Streamlit port
EXPOSE 8507

# Configure Streamlit
ENV STREAMLIT_SERVER_PORT=8507
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8507", "--server.address=0.0.0.0"]
