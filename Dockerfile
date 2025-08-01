# ---------------------------------------------------------------------------- #
#                         Stage 1: Download the models                         #
# ---------------------------------------------------------------------------- #
FROM alpine/git:2.43.0 as download

# NOTE: CivitAI usually requires an API token, so you need to add it in the header
#       of the wget command if you're using a model from CivitAI.
RUN apk add --no-cache wget && \
    wget -q -O /model.safetensors https://huggingface.co/XpucT/Deliberate/resolve/main/Deliberate_v6.safetensors

# ---------------------------------------------------------------------------- #
#                        Stage 2: Build the final image                        #
# ---------------------------------------------------------------------------- #
FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime as build_final_image

ARG A1111_RELEASE=v1.9.3

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_PREFER_BINARY=1 \
    ROOT=/stable-diffusion-webui \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apt-get update && \
    apt install -y \
    fonts-dejavu-core rsync git jq moreutils aria2 wget libgoogle-perftools-dev libtcmalloc-minimal4 procps libgl1 libglib2.0-0 && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/* && apt-get clean -y

# Verify CUDA and PyTorch installation
RUN python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'GPU count: {torch.cuda.device_count()}')" || echo "CUDA verification failed, but continuing..."

# Clone and setup Automatic1111 WebUI
RUN --mount=type=cache,target=/root/.cache/pip \
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git && \
    cd stable-diffusion-webui && \
    git reset --hard ${A1111_RELEASE}

# Install xformers compatible with CUDA 12.8 and PyTorch 2.7.0
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install xformers --index-url https://download.pytorch.org/whl/cu128

# Install other WebUI requirements, but skip PyTorch (already installed)
RUN --mount=type=cache,target=/root/.cache/pip \
    cd stable-diffusion-webui && \
    sed -i '/torch==/d; /torchvision==/d; /torchaudio==/d' requirements_versions.txt && \
    pip install -r requirements_versions.txt && \
    python -c "from launch import prepare_environment; prepare_environment()" --skip-torch-cuda-test

COPY --from=download /model.safetensors /model.safetensors

# Create network volume mount point (RunPod mounts at /runpod-volume)
RUN mkdir -p /runpod-volume/models/checkpoints /runpod-volume/models/loras /runpod-volume/models/embeddings

# Create persistent pip cache directory for A1111 dependencies
RUN mkdir -p /runpod-volume/.cache/a1111/pip

# Configure pip to use RunPod volume cache for persistent caching across container restarts
ENV PIP_CACHE_DIR=/runpod-volume/.cache/a1111/pip

# install dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

COPY test_input.json .

ADD src .

RUN chmod +x start.sh cuda_test.py
CMD ./start.sh
