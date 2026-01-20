# Use an official PyTorch image with CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Utilities
RUN pip install runpod requests boto3 python-dotenv

# pre-install HEAVY video specific dependencies (optimization) often required for video tasks
# done here so they are cached and dont re-download if repo changes. (done before git clone)
RUN pip install imageio imageio-ffmpeg einops fvcore tensorboard scipy

# 3. Clone Official VEnhancer Repo
RUN git clone https://github.com/Vchitect/Vchitect-2.0.git

# 4. Install VEnhancer Dependencies
WORKDIR /app/Vchitect-2.0
RUN pip install -r requirements.txt


# 5. BAKE WEIGHTS (CRITICAL STEP)
# We download the model now so we don't download it on every API call.
# Model: VEnhancer_v2.pt (~5GB)
RUN mkdir -p /app/Vchitect-2.0/ckpts
RUN wget -O /app/Vchitect-2.0/ckpts/vchitect_2.0_2b.pt "https://modelscope.cn/api/v1/models/vchitect/Vchitect-2.0-2B/repo?Revision=master&FilePath=vchitect_2.0_2b.pt"

# 6. Setup Handler
WORKDIR /app
ADD handler.py /app/handler.py

# 7. Start Command
CMD [ "python", "-u", "/app/handler.py" ]
