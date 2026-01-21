# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a containerized VEnhancer (video upscaling) server deployed on RunPod using Cloudflare R2 for storage. The project provides:
- `handler.py` - Server-side inference handler for RunPod serverless endpoints
- `run.py` - Client-side GUI script to upload videos, trigger upscaling, and download results
- `Dockerfile` - Builds a container with baked-in VEnhancer model weights (~5GB) for fast cold starts

## Architecture

**Flow:** Local Upload → R2 (S3-compatible) → RunPod (VEnhancer inference) → R2 (output) → Download

The Docker image is pre-baked with the VEnhancer model weights (`venhancer_v2.pt` from HuggingFace) to avoid slow downloads during cold starts.

## Environment Variables

Required variables in `.env`:
- `RUNPOD_API_KEY` - RunPod authentication
- `RUNPOD_ENDPOINT_ID` - RunPod endpoint ID (in format `https://api.runpod.ai/v2/<id>/run`)
- `AWS_ACCESS_KEY` / `AWS_SECRET_KEY` - R2 credentials
- `S3_BUCKET` - R2 bucket name
- `AWS_ENDPOINT_URL` - R2 endpoint (e.g., `https://<id>.r2.cloudflarestorage.com`)
- `PUBLIC_BASE_URL` - Public R2 URL (e.g., `https://<id>.r2.dev`)

## Build & Deploy

```bash
# Build Docker image
docker build -t <username>/venhancer-serverless:v1 .

# Push to Docker Hub
docker push <username>/venhancer-serverless:v1

# Update RunPod endpoint (after pushing new image)
```

## Running Local Inference

```bash
python run.py
```

Opens a file dialog to select a video, uploads it to R2, triggers the RunPod job, and downloads the enhanced output.

## Inference Parameters

The handler uses `--noise_aug 200` by default in `handler.py:56` to add texture and prevent the "oily/plastic" look typical of ESRGAN-style upscalers. This value can be adjusted based on desired visual quality.

Note: Serverless endpoints have timeout limits (typically 30 minutes), so very long videos may need to be chunked.
