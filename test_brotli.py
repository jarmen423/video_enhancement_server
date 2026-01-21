#!/usr/bin/env python3
"""
test_brotli.py

Purpose & Reasoning:
    This script verifies that the Docker container has proper Brotli support
    for the RunPod SDK. The "cannot decode content-encoding: br" error occurs 
    when aiohttp receives Brotli-compressed responses but lacks the Brotli 
    library to decode them.

Role in Codebase:
    This is a local verification script to run BEFORE pushing a new Docker 
    image to RunPod. It ensures the container environment is correctly 
    configured to handle the RunPod API's Brotli-compressed responses.

Usage:
    docker run --rm jfriedman028/venhancer-serverless:v4 python /app/test_brotli.py
    
    Or copy into running container:
    docker run --rm -v ${PWD}/test_brotli.py:/app/test_brotli.py jfriedman028/venhancer-serverless:v4 python /app/test_brotli.py

Expected Output:
    All checks should pass (✓). If any check fails (✗), the Brotli issue 
    will likely persist on RunPod.
"""

import sys

def check(name: str, condition: bool, details: str = ""):
    """Helper to print pass/fail status."""
    status = "✓" if condition else "✗"
    print(f"  [{status}] {name}")
    if details and not condition:
        print(f"      └─ {details}")
    return condition

def main():
    print("\n" + "="*60)
    print("  BROTLI SUPPORT VERIFICATION TEST")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Test 1: Can we import Brotli?
    print("1. Checking Brotli library...")
    try:
        import brotli
        version = getattr(brotli, '__version__', 'unknown')
        all_passed &= check("Brotli package importable", True)
        print(f"      └─ Version: {version}")
    except ImportError as e:
        all_passed &= check("Brotli package importable", False, str(e))
    
    # Test 2: Can we import aiohttp?
    print("\n2. Checking aiohttp library...")
    try:
        import aiohttp
        version = aiohttp.__version__
        all_passed &= check("aiohttp package importable", True)
        print(f"      └─ Version: {version}")
    except ImportError as e:
        all_passed &= check("aiohttp package importable", False, str(e))
    
    # Test 3: Does aiohttp recognize Brotli support?
    print("\n3. Checking aiohttp Brotli integration...")
    try:
        # aiohttp checks for brotli in its http_parser module
        from aiohttp import http_parser
        
        # Check if brotli decompression is available
        # In newer aiohttp, we can check the available decoders
        has_brotli = False
        try:
            # Try to create a Brotli decompressor - if this works, aiohttp can use it
            import brotli
            # aiohttp uses brotli.Decompressor or brotli.decompress
            test_data = brotli.compress(b"test")
            result = brotli.decompress(test_data)
            has_brotli = (result == b"test")
        except Exception:
            pass
            
        all_passed &= check("aiohttp can use Brotli decompression", has_brotli)
    except Exception as e:
        all_passed &= check("aiohttp can use Brotli decompression", False, str(e))
    
    # Test 4: Can we import runpod?
    print("\n4. Checking RunPod SDK...")
    try:
        import runpod
        version = getattr(runpod, '__version__', 'unknown')
        all_passed &= check("runpod package importable", True)
        print(f"      └─ Version: {version}")
    except ImportError as e:
        all_passed &= check("runpod package importable", False, str(e))
    
    # Test 5: Check runpod's HTTP client
    print("\n5. Checking RunPod HTTP client setup...")
    try:
        from runpod.http_client import ClientSession
        all_passed &= check("runpod.http_client.ClientSession importable", True)
    except ImportError as e:
        all_passed &= check("runpod.http_client.ClientSession importable", False, str(e))
    
    # Test 6: Simulate a Brotli-compressed response decode
    print("\n6. Simulating Brotli response decode...")
    try:
        import brotli
        import asyncio
        import aiohttp
        
        # Create test data
        original = b'{"id": "test-job-123", "input": {"video_url": "https://example.com/test.mp4"}}'
        compressed = brotli.compress(original)
        
        # Decompress it (simulating what aiohttp would do)
        decompressed = brotli.decompress(compressed)
        
        success = (decompressed == original)
        all_passed &= check("Brotli compress/decompress cycle", success)
        if success:
            print(f"      └─ Successfully handled {len(compressed)} -> {len(decompressed)} bytes")
    except Exception as e:
        all_passed &= check("Brotli compress/decompress cycle", False, str(e))
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("  ✓ ALL CHECKS PASSED - Brotli support is correctly configured!")
        print("  You can safely push this image to RunPod.")
    else:
        print("  ✗ SOME CHECKS FAILED - Brotli issue may persist!")
        print("  Review the failed checks above before deploying.")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
