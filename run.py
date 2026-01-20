# Run this python code in your pipeline to trigger the job:
import os
import runpod
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
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL") # r2.dev url
# configure runpod
runpod.api_key = RUNPOD_API_KEY
endpoint = runpod.Endpoint(ENDPOINT_ID)
# configure s3 client for local upload
s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    endpoint_url=ENDPOINT_URL,
    region_name="auto"
)

def main():
    # step 1 - pick filel
    root = tk.Tk(); root.withdraw()
    local_path = filedialog.askopenfilename()
    if not local_path: return

    file_name = os.path.basename(local_path)

    # step 2 - upload to R2 (management link)
    print(f'uploading {file_name} to R2...')
    s3_client.upload_file(local_path, BUCKET_NAME, file_name)

    video_url = f'{PUBLIC_BASE_URL}/{file_name}'

    # step 4 - runpod api call
    print(f'triggering runpod for: {video_url}')
    run_request = endpoint.run({"input": {"video_url": video_url, "upscale_factor": 4}})

    result = run_request.output()

    # step 5: download result
    if "output_url" in result:
        print("success! downloading 4k render...")
        r = requests.get(result['output_url'])
        with open(f'enhanced_{file_name}', 'wb') as f:
            f.write(r.content)
        print("Done!")
if __name__ == "__main__":
    main()
    