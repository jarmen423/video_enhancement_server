# VEnhancer Serverless Dockerfile
# 
# CRITICAL: VEnhancer requires xformers==0.0.21 which needs PyTorch 2.0.1 + CUDA 11.8
# Using NVIDIA's official PyTorch container for proven compatibility
#
FROM nvcr.io/nvidia/pytorch:23.06-py3

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget ffmpeg libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Clone VEnhancer repo first (for requirements reference)
RUN git clone https://github.com/Vchitect/VEnhancer.git /app/VEnhancer

# 3. Install Python dependencies with EXACT pinned versions
# These versions are proven compatible with xformers 0.0.21 + PyTorch 2.0.1
RUN pip install --no-cache-dir \
    # RunPod SDK and dependencies
    runpod==1.7.0 \
    aiohttp==3.9.5 \
    brotli==1.1.0 \
    requests==2.31.0 \
    boto3==1.34.0 \
    python-dotenv==1.0.0 \
    # VEnhancer core dependencies - PINNED versions
    opencv-python-headless==4.10.0.84 \
    easydict==1.13 \
    einops==0.8.0 \
    open-clip-torch==2.20.0 \
    fairscale==0.4.13 \
    torchsde==0.2.6 \
    pytorch-lightning==2.0.1 \
    diffusers==0.30.0 \
    huggingface_hub==0.23.3 \
    imageio==2.34.0 \
    imageio-ffmpeg==0.4.9 \
    # Pin numpy to 1.24.x (required by VEnhancer, compatible with this PyTorch)
    "numpy>=1.24,<1.25"

# 4. Install xformers SEPARATELY with exact version
# xformers 0.0.21 is compiled against PyTorch 2.0.1 + CUDA 11.8
RUN pip install --no-cache-dir xformers==0.0.21

# 5. Download model weights (~5GB) - baked into image to avoid cold start downloads
RUN mkdir -p /app/VEnhancer/ckpts && \
    wget -q --show-progress -O /app/VEnhancer/ckpts/venhancer_v2.pt \
    "https://huggingface.co/jwhejwhe/VEnhancer/resolve/main/venhancer_v2.pt?download=true"

# 6. Copy handler
COPY handler.py /app/handler.py

# 7. Create working directories
RUN mkdir -p /app/input /app/output

# 8. Verify installation works (fail fast if broken)
RUN python -c "import torch; import xformers; import diffusers; print(f'PyTorch: {torch.__version__}, xformers: {xformers.__version__}')"

CMD ["python", "-u", "/app/handler.py"]
