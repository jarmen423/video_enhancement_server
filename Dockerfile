# Use the official RunPod PyTorch image which has proper aiohttp/Brotli support
# This base image is maintained by RunPod and handles the SDK compatibility issues
FROM runpod/pytorch:1.0.3-cu1290-torch280-ubuntu2204

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. Install System Dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y \
    git wget ffmpeg libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Utilities
# Optimized python install - copy requirements first so that changing code doesnt trigger a full re-install
RUN wget -O requirements_cache.txt https://raw.githubusercontent.com/Vchitect/VEnhancer/main/requirements.txt
# Remove 'torch' and 'torchvision' from the downloaded file so they don't conflict with the base image's optimized versions.
RUN sed -i '/torch/d' requirements_cache.txt && \
    sed -i '/opencv/d' requirements_cache.txt

# Use cache mounts for pip to avoid redownloading 500MB+ of libraries
# Note: runpod/pytorch base image should already have runpod SDK with proper Brotli support
# We reinstall/upgrade to be sure, plus add Brotli explicitly as a fallback
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade runpod aiohttp Brotli \
    && pip install requests boto3 python-dotenv imageio imageio-ffmpeg einops fvcore tensorboard scipy \
    && pip install -r requirements_cache.txt

# 3. Clone Official VEnhancer Repo
# BAKE WEIGHTS (CRITICAL STEP)
# We download the model now so we don't download it on every API call.
# Model: VEnhancer_v2.pt (~5GB)
RUN git clone https://github.com/Vchitect/VEnhancer.git /app/VEnhancer

RUN mkdir -p /app/VEnhancer/ckpts && \
    wget -O /app/VEnhancer/ckpts/venhancer_v2.pt "https://huggingface.co/jwhejwhe/VEnhancer/resolve/main/venhancer_v2.pt?download=true"

# 4. Setup Handler and Test Script
COPY handler.py /app/handler.py
COPY test_brotli.py /app/test_brotli.py

# 5. Start Command
CMD [ "python", "-u", "/app/handler.py" ]
