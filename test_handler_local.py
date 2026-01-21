
import sys
import asyncio
sys.path.insert(0, 'd:/code/video_enhancement_server/.venv-venhancer/Lib/site-packages')

from runpod.serverless.modules.rp_job import run_job
from handler import handler


async def main():
    test_job = {
        "id": "local_test_job_123",
        "input": {
            "video_url": "https://pub-70f70f250ef64391aba10aad207fe8d4.r2.dev/test_video.mp4",
            "upscale_factor": 4
        }
    }

    print("Running handler with test job...")
    result = await run_job(handler, test_job)
    print(f"run_job returned: {result}")
    print(f"Type of run_job returned: {type(result)}")

    if "output" in result:
        print(f"Output key exists, output value: {result['output']}")
        print(f"Type of output value: {type(result['output'])}")


if __name__ == "__main__":
    asyncio.run(main())
