# **VEnhancer Serverless Deployment Guide (RunPod)**

This guide outlines how to containerize **VEnhancer** (the official Vchitect implementation) as a serverless endpoint on RunPod. This setup avoids the "oily/plastic" look of Real-ESRGAN by using video diffusion.

## **🏗 Architecture Overview**

1. **Container:** Custom Docker image based on PyTorch \+ CUDA. `jfriedman028/vchitect-2.0-serverless:v1`
2. **Storage:** Cloudflare R2 (S3-Compatible) 
3. **Core Logic:** Clones Vchitect/VEnhancer (Official Repo).  
4. **Optimization:** "Bakes" the 5GB+ model weights into the image during build time to prevent slow cold starts.  
5. **Interface:** A handler.py script that accepts a JSON payload, runs inference, and uploads the result.
6. **Flow:** Local Upload -> Public URL -> RunPod -> R2 Upload -> Public URL download.

## **📂 File 1: handler.py (Server-Side)**

*Save this in your project root.*

```python
import runpod
import subprocess
import os
import requests
import shutil
import boto3
from urllib.parse import urlparse

# --- Configuration ---
VCHITECT_DIR = "/app/Vchitect-2.0"
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

def download_file(url, destination):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(destination, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

def get_s3_client():
    # Explicit check to prevent silent failures
    if not os.environ.get("AWS_ACCESS_KEY"):
        raise ValueError("Missing AWS_ACCESS_KEY env var")
    
    return boto3.client(
        's3',
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_KEY"),
        endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        region_name="auto"
    )

def handler(job):
    job_input = job['input']
    
    # 1. Parse Inputs
    video_url = job_input.get('video_url')
    if not video_url:
        return {"error": "Missing 'video_url' in input"}
        
    upscale_factor = str(job_input.get('upscale_factor', '4'))
    
    # 2. Cleanup & Prepare Directories (Robust Method)
    for d in [INPUT_DIR, OUTPUT_DIR]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except OSError:
                pass # Handle edge case where file is locked
        os.makedirs(d, exist_ok=True)
    
    input_path = os.path.join(INPUT_DIR, "input.mp4")

    # 3. Download Input
    try:
        print(f"Downloading from {video_url}...")
        download_file(video_url, input_path)
    except Exception as e:
        return {"error": f"Download failed: {str(e)}"}

    # 4. Run Inference
    # Note: Vchitect-2.0 uses 'inference.py'
    command = [
        "python", "inference.py",
        "--input_path", INPUT_DIR,
        "--save_dir", OUTPUT_DIR,
        "--up_scale", upscale_factor,
        "--noise_aug", "200" # Adds texture to prevent 'oily' look
    ]

    try:
        print("Starting Vchitect Inference...")
        subprocess.check_call(command, cwd=VCHITECT_DIR)
    except subprocess.CalledProcessError as e:
        return {"error": f"Inference failed exit code: {e.returncode}"}

    # 5. Upload Output
    output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
    if not output_files:
        return {"error": "No output video found after inference."}
    
    final_video = os.path.join(OUTPUT_DIR, output_files[0])
    s3_key = f"vchitect_output_{job['id']}.mp4"
    
    try:
        s3 = get_s3_client()
        bucket = os.environ.get("S3_BUCKET")
        if not bucket: raise ValueError("S3_BUCKET env var missing")

        print(f"Uploading to {bucket}/{s3_key}...")
        s3.upload_file(final_video, bucket, s3_key)
        
        # Construct Public Download URL
        public_base = os.environ.get("PUBLIC_BASE_URL", "").rstrip('/')
        if not public_base:
            return {"error": "PUBLIC_BASE_URL env var missing"}
            
        output_url = f"{public_base}/{s3_key}"
        return {"status": "success", "output_url": output_url}
        
    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}

runpod.serverless.start({"handler": handler})
```
## **File 2: `run.py` (Client-Side):**
*Run on local computer. Now handles filenames with spaces correctly*
```python
import os
import requests
import runpod
import boto3
import tkinter as tk
from tkinter import filedialog
from dotenv import load_dotenv
from urllib.parse import quote

# 1. Load Config
load_dotenv()
REQUIRED_VARS = ["RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID", "AWS_ACCESS_KEY", "AWS_SECRET_KEY", "S3_BUCKET", "AWS_ENDPOINT_URL", "PUBLIC_BASE_URL"]
for var in REQUIRED_VARS:
    if not os.getenv(var):
        print(f"❌ Error: Missing {var} in .env file")
        exit(1)

runpod.api_key = os.getenv("RUNPOD_API_KEY")
endpoint = runpod.Endpoint(os.getenv("RUNPOD_ENDPOINT_ID"))

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
    region_name="auto"
)

def main():
    # 1. Pick File
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    local_path = filedialog.askopenfilename(title="Select Video")
    root.destroy()

    if not local_path:
        print("No file selected.")
        return

    # 2. Upload to R2
    file_name = os.path.basename(local_path)
    # Sanitize filename for URL safety (spaces -> %20)
    safe_file_name = quote(file_name) 
    
    print(f"⬆️ Uploading {file_name} to R2...")
    try:
        s3_client.upload_file(local_path, os.getenv("S3_BUCKET"), safe_file_name)
    except Exception as e:
        print(f"Upload failed: {e}")
        return

    # 3. Create Public URL
    video_url = f"{os.getenv('PUBLIC_BASE_URL')}/{safe_file_name}"

    # 4. Trigger RunPod
    print(f"🚀 Triggering Upscale for: {video_url}")
    try:
        run_request = endpoint.run({
            "input": {
                "video_url": video_url,
                "upscale_factor": 4
            }
        })
    except Exception as e:
        print(f"Failed to connect to RunPod: {e}")
        return

    # 5. Wait & Download
    print(f"⏳ Waiting for Job {run_request.job_id}...")
    result = run_request.output() # Blocking call

    if "output_url" in result:
        print("⬇️ Downloading result...")
        r = requests.get(result['output_url'])
        output_name = f"enhanced_{file_name}"
        with open(output_name, "wb") as f:
            f.write(r.content)
        print(f"✅ Success! Saved as {output_name}")
    else:
        print(f"❌ Job Failed: {result}")

if __name__ == "__main__":
    main()
```
## **🐳 File 3: Dockerfile**

*Save this in the same directory.*

```Dockerfile
# Use an official PyTorch image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Utilities
RUN pip install runpod requests boto3 python-dotenv

# pre-install HEAVY video specific dependencies (optimization) often required for video tasks
# done here so they are cached and dont re-download if repo changes. (done before git clone)
RUN pip install imageio imageio-ffmpeg einops fvcore tensorboard scipy

# 3. Clone Official VEnhancer Repo
RUN git clone https://github.com/Vchitect/Vchitect-2.0.git

# 4. Install VEnhancer Dependencies
WORKDIR /app/Vchitect-2.0
RUN pip install -r requirements.txt


# 5. BAKE WEIGHTS (CRITICAL STEP)
# We download the model now so we don't download it on every API call.
# Model: VEnhancer_v2.pt (~5GB)
RUN mkdir -p /app/Vchitect-2.0/ckpts
RUN wget -O /app/Vchitect-2.0/ckpts/vchitect_2.0_2b.pt "https://modelscope.cn/api/v1/models/vchitect/Vchitect-2.0-2B/repo?Revision=master&FilePath=vchitect_2.0_2b.pt"

# 6. Setup Handler
WORKDIR /app
ADD handler.py /app/handler.py

# 7. Start Command
CMD [ "python", "-u", "/app/handler.py" ]

```

## **🚀 Deployment Instructions**

### **Step 1: Build & Push**

Open your terminal in the project folder:

\# 1\. Login to Docker Hub  
docker login

\# 2\. Build the image (This will take time due to the 5GB model download)  
docker build \-t yourusername/venhancer-serverless:v1 .

\# 3\. Push to Docker Hub  
docker push yourusername/venhancer-serverless:v1

### **Step 2: Configure RunPod**

1. Go to **RunPod Console** \> **Serverless** \> **New Endpoint**.  
2. **Container Image:** yourusername/venhancer-serverless:v1  
3. **Container Disk:** 20 GB (The image itself is large).  
4. **GPU Type:** RTX 3090 or RTX 4090 (Recommended).  
5. **Environment Variables** (If using S3):  
   * AWS\_ACCESS\_KEY: your\_key  
   * AWS\_SECRET\_KEY: your\_secret  
   * S3\_BUCKET: your\_bucket\_name

### **Step 3: run.py**

## **💡 Pro-Tips for Quality**

1. **The "Oily" Factor:**  
   * The parameter \--noise\_aug in handler.py controls the added texture.  
   * **200-300:** Cinematic, realistic grain (Recommended).  
   * **0-50:** Cleaner, but risks looking like plastic (ESRGAN style).  
   * **Logic:** If your result looks too noisy, lower this value in the handler.  
2. **Video Duration:**  
   * Serverless endpoints have timeouts (usually 30 mins max).  
   * VEnhancer is heavy. If your video is \> 3 minutes long, consider splitting it into chunks before sending, or switch to a standard Pod deployment.  
3. **Cold Starts:**  
   * Because the Docker image is large (\~10GB including weights), the very first run might take 2-4 minutes to boot. Enable **FlashBoot** on RunPod if available to cache the image.
   
