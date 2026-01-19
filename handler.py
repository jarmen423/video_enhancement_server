import runpod
import subprocess
import os
import requests
import shutil
import boto3
from botocore.exceptions import NoCredentialsError

# --- Configuration ---
VENHANCER_DIR = "/app/VEnhancer"
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

# S3 Configuration (Optional but Recommended for Video)
S3_BUCKET = os.environ.get("S3_BUCKET", "my-bucket")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY")

def download_file(url, destination):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(destination, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

def upload_to_s3(local_file, s3_file):
    """Uploads result to S3 and returns the presigned URL or public URL"""
    if not AWS_ACCESS_KEY:
        return "S3 Credentials not set - file saved locally on pod"
    
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    try:
        s3.upload_file(local_file, S3_BUCKET, s3_file)
        # Return a signed URL valid for 1 hour
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': S3_BUCKET, 'Key': s3_file},
                                        ExpiresIn=3600)
        return url
    except Exception as e:
        return f"S3 Upload Failed: {str(e)}"

def handler(job):
    job_input = job['input']
    
    # 1. Parse Inputs
    video_url = job_input.get('video_url')
    upscale_factor = str(job_input.get('upscale_factor', '4'))
    version = str(job_input.get('version', 'v2')) # 'v2' is best for texture
    
    # 2. Prepare Environment
    if os.path.exists(INPUT_DIR): shutil.rmtree(INPUT_DIR)
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    input_path = os.path.join(INPUT_DIR, "input.mp4")

    # 3. Download Video
    try:
        print(f"Downloading video from {video_url}...")
        download_file(video_url, input_path)
    except Exception as e:
        return {"error": f"Download failed: {str(e)}"}

    # 4. Run Inference
    # Note: --noise_aug 200 is critical for preventing the "oily" look
    command = [
        "python", "enhance_a_video.py",
        "--input_path", INPUT_DIR,
        "--save_dir", OUTPUT_DIR,
        "--version", version, 
        "--up_scale", upscale_factor,
        "--noise_aug", "200", 
        "--solver_mode", "fast",
        "--filename_as_prompt", "True"
    ]

    try:
        print("Starting Inference...")
        subprocess.check_call(command, cwd=VENHANCER_DIR)
    except subprocess.CalledProcessError:
        return {"error": "Inference failed. Check logs."}

    # 5. Handle Output
    output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
    if not output_files:
        return {"error": "No output video generated."}
    
    final_video = os.path.join(OUTPUT_DIR, output_files[0])
    s3_key = f"enhanced_{job['id']}.mp4"
    
    # Upload to S3
    result_url = upload_to_s3(final_video, s3_key)
    
    return {"status": "success", "output_url": result_url}

runpod.serverless.start({"handler": handler})
