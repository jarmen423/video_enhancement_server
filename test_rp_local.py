
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from runpod.serverless.modules.rp_local import run_local
from handler import handler

async def main():
    # Test configuration
    config = {
        "handler": handler,
        "rp_args": {
            "test_input": {
                "id": "test123",
                "input": {
                    "video_url": "https://www.example.com/test.mp4",
                    "upscale_factor": 4
                }
            }
        }
    }
    
    await run_local(config)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
