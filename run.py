# Run this python code in your pipeline to trigger the job:
import runpod

runpod.api_key = "YOUR_RUNPOD_API_KEY"
endpoint = runpod.Endpoint("YOUR_ENDPOINT_ID")

run_request = endpoint.run({
    "input": {
        "video_url": "[https://example.com/my_lowres_video.mp4](https://example.com/my_lowres_video.mp4)",
        "upscale_factor": 4,
        "version": "v2"
    }
})

print("Job started...")
print(run_request.output()) # Will wait and print the S3 URL when done
