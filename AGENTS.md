# AGENTS.md

This file provides guidance for coding agents working with the video_enhancement_server repository.

## Build/Lint/Test Commands

### Build Commands
```bash
# Build Docker image (includes model weights ~5GB)
docker build -t <username>/venhancer-serverless:v1 .

# Push to Docker Hub
docker push <username>/venhancer-serverless:v1
```

### Test Commands
```bash
# Run individual test files
python test_handler_local.py
python test_rp_local.py
python test_brotli.py

# Test Brotli support in Docker container
docker run --rm <image> python /app/test_brotli.py
```

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run local client
python run.py
```

## Code Style Guidelines

### Python Standards
- **Python Version**: 3.8+ (based on dependencies and syntax)
- **Line Length**: 120 characters max (observed in codebase)
- **Indentation**: 4 spaces (standard Python)
- **Encoding**: UTF-8 for all files

### Imports
```python
# Group imports in this order:
import os
import sys
import asyncio

# Third-party imports
import boto3
import requests
import runpod

# Local imports (if any)
from . import local_module
```

### Naming Conventions
- **Functions/Methods**: `snake_case` (e.g., `download_file`, `get_s3_client`)
- **Variables**: `snake_case` (e.g., `video_url`, `input_path`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `VCHITECT_DIR`, `INPUT_DIR`)
- **Classes**: `PascalCase` (rare in this codebase)
- **Environment Variables**: `UPPER_SNAKE_CASE` (e.g., `AWS_ACCESS_KEY`)

### Documentation
- **Docstrings**: Use triple quotes with detailed explanations
- **Purpose Section**: Always include "Purpose & Reasoning" for complex functions
- **Args/Raises**: Document parameters and exceptions
- **Inline Comments**: Explain complex logic, not obvious code

```python
def download_file(url, destination):
    """
    Downloads a file from the given URL to the destination path.

    Purpose & Reasoning:
        We must be very explicit about avoiding Brotli (br) compression because...

    Args:
        url: The public URL of the file to download (e.g., R2 public link).
        destination: Local filesystem path to save the downloaded file.

    Raises:
        requests.HTTPError: If the HTTP request returns an error status code.
    """
```

### Error Handling
- **Explicit Exception Handling**: Use try/except blocks for all external operations
- **Specific Exceptions**: Catch specific exceptions, not bare `Exception`
- **Error Messages**: Provide clear, actionable error messages
- **Logging**: Use print() for debugging, not logging module (observed pattern)

```python
try:
    download_file(video_url, input_path)
except Exception as e:
    return {"error": f"Download failed: {str(e)}"}
```

### Environment Variables
- **Access Pattern**: Use `os.environ.get("VAR_NAME")` for optional vars
- **Validation**: Check required env vars at startup
- **Security**: Never log or expose secret keys

```python
def get_s3_client():
    # Explicit check to prevent silent failures
    if not os.environ.get("AWS_ACCESS_KEY"):
        raise ValueError("Missing AWS_ACCESS_KEY env var")

    return boto3.client(...)
```

### File Operations
- **Path Handling**: Use `os.path.join()` for cross-platform compatibility
- **Directory Creation**: Use `os.makedirs(d, exist_ok=True)`
- **Cleanup**: Remove temp directories with `shutil.rmtree(d)`
- **File Extensions**: Check with `f.endswith('.mp4')`

### Async/Await
- **When to Use**: For I/O operations and RunPod SDK calls
- **Event Loop**: Use `asyncio.run(main())` in `__main__` blocks

### HTTP Requests
- **Headers**: Explicitly set `Accept-Encoding` to avoid compression issues
- **Timeouts**: Always set reasonable timeouts (e.g., `timeout=300`)
- **Response Handling**: Use `response.raise_for_status()` then `response.content`

### AWS/R2 Operations
- **Client Creation**: Create S3 clients per operation, not globally
- **Region**: Use `region_name="auto"` for Cloudflare R2
- **URLs**: Construct public URLs from base URL + key

### Security Best Practices
- **Secrets**: Never commit `.env` files or hardcode credentials
- **Input Validation**: Validate all user inputs before processing
- **Error Messages**: Don't expose internal paths or sensitive information
- **Dependencies**: Pin versions in `requirements.txt`

### Code Structure
- **Function Length**: Keep functions focused and under 50 lines when possible
- **Global Constants**: Define configuration constants at module level
- **Main Function**: Use `if __name__ == "__main__":` pattern
- **Exit Codes**: Use `sys.exit(1)` for errors

### Testing
- **Test Files**: Name as `test_*.py`
- **Test Structure**: Create realistic test inputs matching production
- **Mock External Services**: Test logic without actual API calls when possible
- **Integration Tests**: Test full pipeline with local RunPod SDK

### Docker Considerations
- **Model Weights**: Pre-download large models in Docker build (not runtime)
- **Dependencies**: Install heavy packages early in Dockerfile for caching
- **Brotli Support**: Ensure `brotli` package is installed for RunPod SDK
- **Working Directory**: Use absolute paths in containers (`/app/...`)

### Performance
- **Cold Starts**: Minimize dependencies loaded at startup
- **Memory Usage**: Clean up temp files and directories immediately
- **Network**: Use streaming downloads for large files
- **Concurrency**: Consider async operations for multiple concurrent jobs

### Deployment
- **Environment Variables**: Document all required env vars
- **Container Registry**: Tag images with semantic versions
- **Configuration**: Separate config from code using environment variables
- **Monitoring**: Log key operations for debugging production issues</content>
<parameter name="filePath">/home/josh/code/video_enhancement_server/AGENTS.md