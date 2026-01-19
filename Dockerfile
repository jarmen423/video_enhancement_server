# Use an official PyTorch image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Utilities
RUN pip install runpod requests boto3

# 3. Clone Official VEnhancer Repo
RUN git clone https://github.com/Vchitect/VEnhancer.git

# 4. Install VEnhancer Dependencies
WORKDIR /app/VEnhancer
# Installing specific dependencies often required for video tasks
RUN pip install imageio imageio-ffmpeg einops fvcore tensorboard scipy

# 5. BAKE WEIGHTS (CRITICAL STEP)
# We download the model now so we don't download it on every API call.
# Model: VEnhancer_v2.pt (~5GB)
RUN mkdir -p ckpts
RUN wget -O ckpts/venhancer_v2.pt https://huggingface.co/Vchitect/VEnhancer/resolve/main/venhancer_v2.pt

# 6. Setup Handler
WORKDIR /app
ADD handler.py /app/handler.py

# 7. Start Command
CMD [ "python", "-u", "/app/handler.py" ]
