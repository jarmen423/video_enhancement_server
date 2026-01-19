# **VEnhancer Serverless Deployment Guide (RunPod)**

This guide outlines how to containerize **VEnhancer** (the official Vchitect implementation) as a serverless endpoint on RunPod. This setup avoids the "oily/plastic" look of Real-ESRGAN by using video diffusion.

## **🏗 Architecture Overview**

1. **Container:** Custom Docker image based on PyTorch \+ CUDA.  
2. **Core Logic:** Clones Vchitect/VEnhancer (Official Repo).  
3. **Optimization:** "Bakes" the 5GB+ model weights into the image during build time to prevent slow cold starts.  
4. **Interface:** A handler.py script that accepts a JSON payload, runs inference, and uploads the result.

## **📂 File 1: handler.py**

*Save this in your project root.*

This script acts as the bridge between RunPod's API and the VEnhancer CLI.

import runpod  
import subprocess  
import os  
import requests  
import shutil  
import boto3  
from botocore.exceptions import NoCredentialsError

\# \--- Configuration \---  
VENHANCER\_DIR \= "/app/VEnhancer"  
INPUT\_DIR \= "/app/input"  
OUTPUT\_DIR \= "/app/output"

\# S3 Configuration (Optional but Recommended for Video)  
S3\_BUCKET \= os.environ.get("S3\_BUCKET", "my-bucket")  
AWS\_ACCESS\_KEY \= os.environ.get("AWS\_ACCESS\_KEY")  
AWS\_SECRET\_KEY \= os.environ.get("AWS\_SECRET\_KEY")

def download\_file(url, destination):  
    with requests.get(url, stream=True) as r:  
        r.raise\_for\_status()  
        with open(destination, 'wb') as f:  
            shutil.copyfileobj(r.raw, f)

def upload\_to\_s3(local\_file, s3\_file):  
    """Uploads result to S3 and returns the presigned URL or public URL"""  
    if not AWS\_ACCESS\_KEY:  
        return "S3 Credentials not set \- file saved locally on pod"  
      
    s3 \= boto3.client('s3', aws\_access\_key\_id=AWS\_ACCESS\_KEY, aws\_secret\_access\_key=AWS\_SECRET\_KEY)  
    try:  
        s3.upload\_file(local\_file, S3\_BUCKET, s3\_file)  
        \# Return a signed URL valid for 1 hour  
        url \= s3.generate\_presigned\_url('get\_object',  
                                        Params={'Bucket': S3\_BUCKET, 'Key': s3\_file},  
                                        ExpiresIn=3600)  
        return url  
    except Exception as e:  
        return f"S3 Upload Failed: {str(e)}"

def handler(job):  
    job\_input \= job\['input'\]  
      
    \# 1\. Parse Inputs  
    video\_url \= job\_input.get('video\_url')  
    upscale\_factor \= str(job\_input.get('upscale\_factor', '4'))  
    version \= str(job\_input.get('version', 'v2')) \# 'v2' is best for texture  
      
    \# 2\. Prepare Environment  
    if os.path.exists(INPUT\_DIR): shutil.rmtree(INPUT\_DIR)  
    if os.path.exists(OUTPUT\_DIR): shutil.rmtree(OUTPUT\_DIR)  
    os.makedirs(INPUT\_DIR, exist\_ok=True)  
    os.makedirs(OUTPUT\_DIR, exist\_ok=True)  
      
    input\_path \= os.path.join(INPUT\_DIR, "input.mp4")

    \# 3\. Download Video  
    try:  
        print(f"Downloading video from {video\_url}...")  
        download\_file(video\_url, input\_path)  
    except Exception as e:  
        return {"error": f"Download failed: {str(e)}"}

    \# 4\. Run Inference  
    \# Note: \--noise\_aug 200 is critical for preventing the "oily" look  
    command \= \[  
        "python", "enhance\_a\_video.py",  
        "--input\_path", INPUT\_DIR,  
        "--save\_dir", OUTPUT\_DIR,  
        "--version", version,   
        "--up\_scale", upscale\_factor,  
        "--noise\_aug", "200",   
        "--solver\_mode", "fast",  
        "--filename\_as\_prompt", "True"  
    \]

    try:  
        print("Starting Inference...")  
        subprocess.check\_call(command, cwd=VENHANCER\_DIR)  
    except subprocess.CalledProcessError:  
        return {"error": "Inference failed. Check logs."}

    \# 5\. Handle Output  
    output\_files \= \[f for f in os.listdir(OUTPUT\_DIR) if f.endswith('.mp4')\]  
    if not output\_files:  
        return {"error": "No output video generated."}  
      
    final\_video \= os.path.join(OUTPUT\_DIR, output\_files\[0\])  
    s3\_key \= f"enhanced\_{job\['id'\]}.mp4"  
      
    \# Upload to S3  
    result\_url \= upload\_to\_s3(final\_video, s3\_key)  
      
    return {"status": "success", "output\_url": result\_url}

runpod.serverless.start({"handler": handler})

## **🐳 File 2: Dockerfile**

*Save this in the same directory.*

This builds the environment and pre-loads the heavy weights.

\# Use an official PyTorch image with CUDA support  
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN\_FRONTEND=noninteractive  
WORKDIR /app

\# 1\. Install System Dependencies  
RUN apt-get update && apt-get install \-y \\  
    git wget ffmpeg libgl1-mesa-glx \\  
    && rm \-rf /var/lib/apt/lists/\*

\# 2\. Install Python Utilities  
RUN pip install runpod requests boto3

\# 3\. Clone Official VEnhancer Repo  
RUN git clone \[https://github.com/Vchitect/VEnhancer.git\](https://github.com/Vchitect/VEnhancer.git)

\# 4\. Install VEnhancer Dependencies  
WORKDIR /app/VEnhancer  
\# Installing specific dependencies often required for video tasks  
RUN pip install imageio imageio-ffmpeg einops fvcore tensorboard scipy

\# 5\. BAKE WEIGHTS (CRITICAL STEP)  
\# We download the model now so we don't download it on every API call.  
\# Model: VEnhancer\_v2.pt (\~5GB)  
RUN mkdir \-p ckpts  
RUN wget \-O ckpts/venhancer\_v2.pt "\[https://huggingface.co/Vchitect/VEnhancer/resolve/main/venhancer\_v2.pt\](https://huggingface.co/Vchitect/VEnhancer/resolve/main/venhancer\_v2.pt)"

\# 6\. Setup Handler  
WORKDIR /app  
ADD handler.py /app/handler.py

\# 7\. Start Command  
CMD \[ "python", "-u", "/app/handler.py" \]

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

### **Step 3: Usage (Client Side)**

Run this Python code in your pipeline to trigger the job:

import runpod

runpod.api\_key \= "YOUR\_RUNPOD\_API\_KEY"  
endpoint \= runpod.Endpoint("YOUR\_ENDPOINT\_ID")

run\_request \= endpoint.run({  
    "input": {  
        "video\_url": "\[https://example.com/my\_lowres\_video.mp4\](https://example.com/my\_lowres\_video.mp4)",  
        "upscale\_factor": 4,  
        "version": "v2"  
    }  
})

print("Job started...")  
print(run\_request.output()) \# Will wait and print the S3 URL when done

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
   
