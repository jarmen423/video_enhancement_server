# Run this python code in your pipeline to trigger the job:
import os
import sys

try:
    import runpod
except ImportError:
    print("Error: runpod module not found.")
    print("Please activate the virtual environment first:")
    print("  On Windows CMD: .venv-venhancer\\Scripts\\activate")
    print("  On Windows PowerShell: .venv-venhancer\\Scripts\\Activate.ps1")
    print("  Then run: python run.py")
    sys.exit(1)

import requests
import boto3
import tkinter as tk
from tkinter import filedialog
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
# cloudflare R2 config
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
SECRET_KEY = os.getenv("AWS_SECRET_KEY")
BUCKET_NAME = os.getenv("S3_BUCKET")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")  # r2.dev url
# configure runpod
runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(ENDPOINT_ID)
# configure s3 client for local upload
s3_client = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=ENDPOINT_URL,
    region_name="auto",
)


def main():
    try:
        # step 1 - pick filel
        print("Opening file dialog...")
        root = tk.Tk()
        root.withdraw()
        local_path = filedialog.askopenfilename()
        if not local_path:
            print("No file selected")
            return
        print(f"Selected file: {local_path}")

        file_name = os.path.basename(local_path)

        # step 2 - upload to R2 (management link)
        print(f"uploading {file_name} to R2...")
        s3_client.upload_file(local_path, BUCKET_NAME, file_name)
        print("Upload complete!")

        video_url = f"{PUBLIC_BASE_URL}/{file_name}"

        # step 4 - runpod api call
        print(f"triggering runpod for: {video_url}")
        
        # NOTE: endpoint.run() expects the input payload directly, NOT wrapped in {"input": ...}
        # The SDK handles the wrapping internally
        input_payload = {"video_url": video_url, "upscale_factor": 4}
        print(f"Sending input payload: {input_payload}")
        
        run_request = endpoint.run(input_payload)
        job_id = run_request.job_id
        print(f"Job submitted with ID: {job_id}")
        print("Polling for completion (this may take a while)...")

        # Poll and show status
        import time
        while True:
            status = run_request.status()
            print(f"Current status: {status}")
            if status == "COMPLETED":
                break
            elif status in ["FAILED", "CANCELLED", "TIMED_OUT"]:
                print(f"Job ended with status: {status}")
                # Fetch full error details via direct API call
                try:
                    status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
                    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
                    resp = requests.get(status_url, headers=headers)
                    error_data = resp.json()
                    print("=" * 50)
                    print("FULL ERROR DETAILS FROM RUNPOD:")
                    import json
                    print(json.dumps(error_data, indent=2))
                    print("=" * 50)
                except Exception as e:
                    print(f"Could not fetch error details: {e}")
                break
            time.sleep(5)  # Poll every 5 seconds

        # Get the result
        result = run_request.output()
        print("=" * 50)
        print(f"Full result received:")
        print(f"  Type: {type(result)}")
        print(f"  Value: {result}")
        print("=" * 50)

        # step 5: download result
        if result and isinstance(result, dict):
            # Check for error in the result
            if "error" in result:
                print(f"Job failed with error: {result['error']}")
            elif "output_url" in result:
                print("success! downloading 4k render...")
                r = requests.get(result["output_url"])
                output_path = f"enhanced_{file_name}"
                with open(output_path, "wb") as f:
                    f.write(r.content)
                print(f"Done! Saved to: {output_path}")
            elif "output" in result and isinstance(result["output"], dict) and "output_url" in result["output"]:
                print("success! downloading 4k render...")
                r = requests.get(result["output"]["output_url"])
                output_path = f"enhanced_{file_name}"
                with open(output_path, "wb") as f:
                    f.write(r.content)
                print(f"Done! Saved to: {output_path}")
            else:
                print(f"Job completed but no output_url found in result keys: {result.keys() if hasattr(result, 'keys') else 'N/A'}")
        else:
            print(f"Job completed but result is not a dict or is None. Result type: {type(result)}, Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
