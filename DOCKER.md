# Docker Usage for Teacher PDF Printer

## Quick Start with Docker Compose (Recommended)

### Build and Run
```bash
docker-compose up --build
```

### Access the Application
Open your browser to: `http://localhost:8507`

### Stop the Application
```bash
docker-compose down
```

## Manual Docker Commands

### Build the Image
```bash
docker build -t teacher-printer .
```

### Run the Container
```bash
docker run -d \
  --name teacher-printer \
  -p 8507:8507 \
  -v $(pwd)/printer_inputs:/app/printer_inputs \
  -v $(pwd)/printer_outputs:/app/printer_outputs \
  -v $(pwd)/printer_processes:/app/printer_processes \
  teacher-printer
```

### Stop the Container
```bash
docker stop teacher-printer
docker rm teacher-printer
```

### View Logs
```bash
docker logs -f teacher-printer
```

## Directory Bindings

The following directories are mounted as volumes to persist data:

- **printer_inputs/**: Uploaded PDF files
- **printer_outputs/**: Generated output PDFs
- **printer_processes/**: Active job data and selections

All data persists on your host machine even when the container is stopped or removed.

## Port Mapping

- **Host Port**: 8507
- **Container Port**: 8507
- Access URL: `http://localhost:8507`

## Environment Variables

Set in Dockerfile and docker-compose.yml:
- `STREAMLIT_SERVER_PORT=8507`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
- `STREAMLIT_SERVER_HEADLESS=true`
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs teacher-printer

# Check if port is already in use
lsof -i :8507
```

### Permission issues with volumes
```bash
# Ensure directories exist and have correct permissions
mkdir -p printer_inputs printer_outputs printer_processes
chmod 755 printer_inputs printer_outputs printer_processes
```

### Rebuild after code changes
```bash
docker-compose down
docker-compose up --build
```
