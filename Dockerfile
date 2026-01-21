# Use an official PyTorch image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. Install System Dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y \
    git wget ffmpeg libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Utilities
# optimized python install , 
# copy requirements first so that changing code doesnt trigger a full re-install
RUN wget -O requirements_cache.txt https://raw.githubusercontent.com/Vchitect/VEnhancer/main/requirements.txt
# remove 'torch' and 'torchvision' from the downloaded file so they dont conflict with the base images optimized versions.
RUN sed -i '/torch/d' requirements_cache.txt && \
    sed -i '/opencv/d' requirements_cache.txt
# use cache mounts for pip to avoid redownloading 500MB+ of libraries
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install runpod requests boto3 python-dotenv imageio imageio-ffmpeg einops fvcore tensorboard scipy brotli \
    && pip install -r requirements_cache.txt

# 3. Clone Official VEnhancer Repo
# BAKE WEIGHTS (CRITICAL STEP)
# We download the model now so we don't download it on every API call.
# Model: VEnhancer_v2.pt (~5GB)
RUN git clone https://github.com/Vchitect/VEnhancer.git /app/Vchitect-2.0

RUN mkdir -p /app/VEnhancer/ckpts && \
    wget -O /app/VEnhancer/ckpts/venhancer_v2.pt "https://huggingface.co/jwhejwhe/VEnhancer/resolve/main/venhancer_v2.pt?download=true"
# 4. Setup Handler
COPY handler.py /app/handler.py

# 5. Start Command
CMD [ "python", "-u", "/app/handler.py" ]
