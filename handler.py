import runpod
import subprocess
import os
import requests
import shutil
import boto3

# --- Configuration ---
# Note: Vchitect-2.0 uses 'inference.py' as the entry point
VCHITECT_DIR = "/app/VEnhancer"
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

def download_file(url, destination):
    """
    Downloads a video file from the given URL.
    
    Now that 'brotli' is added to requirements.txt, 'requests' will 
    automatically handle decompressing responses from R2/Cloudflare.
    """
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    
    with open(destination, 'wb') as f:
        f.write(response.content)

def get_s3_client():
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
    upscale_factor = str(job_input.get('upscale_factor', '4'))
    
    # 2. Prepare Environment
    for d in [INPUT_DIR, OUTPUT_DIR]:
        if os.path.exists(d): shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    
    input_path = os.path.join(INPUT_DIR, "input.mp4")

    # 3. Download Input Video from R2 Public Link
    try:
        download_file(video_url, input_path)
    except Exception as e:
        return {"error": f"Download failed: {str(e)}"}

    # 4. Run VEnhancer Inference
    # The actual script is enhance_a_video.py, not inference.py
    # --noise_aug 200-300 helps prevent the 'oily' look
    prompt = job_input.get('prompt', 'a high quality video')
    command = [
        "python", "enhance_a_video.py",
        "--version", "v2",
        "--model_path", "/app/VEnhancer/ckpts/venhancer_v2.pt",
        "--input_path", input_path,
        "--save_dir", OUTPUT_DIR,
        "--prompt", prompt,
        "--up_scale", upscale_factor,
        "--target_fps", "24",
        "--noise_aug", "200",
        "--solver_mode", "fast",
        "--steps", "15"
    ]

    try:
        subprocess.check_call(command, cwd=VCHITECT_DIR)
    except subprocess.CalledProcessError as e:
        return {"error": f"Inference failed with exit code {e.returncode}"}

    # 5. Upload Output to R2 via S3 API
    output_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp4')]
    if not output_files:
        return {"error": "No output video generated."}
    
    final_video = os.path.join(OUTPUT_DIR, output_files[0])
    s3_key = f"vchitect_2_enhanced_{job['id']}.mp4"
    
    try:
        s3 = get_s3_client()
        s3.upload_file(final_video, os.environ.get("S3_BUCKET"), s3_key)
        
        # Construct the Public URL for the local script to download
        public_base = os.environ.get("PUBLIC_BASE_URL").rstrip('/')
        output_url = f"{public_base}/{s3_key}"
        
        return {"status": "success", "output_url": output_url}
    except Exception as e:
        return {"error": f"Upload to R2 failed: {str(e)}"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})