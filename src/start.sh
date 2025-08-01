#!/usr/bin/env bash

echo "Worker Initiated"

echo "=============================================="
echo "RUNNING CUDA COMPATIBILITY TESTS"
echo "=============================================="

# Run CUDA compatibility test
python ./cuda_test.py
CUDA_TEST_EXIT_CODE=$?

if [ $CUDA_TEST_EXIT_CODE -eq 0 ]; then
    echo "🎉 CUDA compatibility test PASSED - RTX 6000 Ada ready!"
elif [ $CUDA_TEST_EXIT_CODE -eq 1 ]; then
    echo "⚠ CUDA test passed with warnings - continuing with reduced performance"
else
    echo "❌ CUDA compatibility test FAILED"
    echo "❌ RTX 6000 Ada may not be properly supported"
    echo "❌ Check the logs above for details"
    echo "⚠ Attempting to continue anyway..."
fi

echo ""
echo "=============================================="
echo "STARTING WEBUI API"
echo "=============================================="

# Setup memory optimization
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true

# Check if WebUI directory exists
if [ ! -d "/stable-diffusion-webui" ]; then
    echo "❌ ERROR: /stable-diffusion-webui directory not found!"
    echo "Available directories in root:"
    ls -la /
    exit 1
fi

# Check if webui.py exists
if [ ! -f "/stable-diffusion-webui/webui.py" ]; then
    echo "❌ ERROR: /stable-diffusion-webui/webui.py not found!"
    echo "Contents of /stable-diffusion-webui:"
    ls -la /stable-diffusion-webui/
    exit 1
fi

# Clean WebUI cache to prevent SQLite schema issues
echo "🧹 Cleaning WebUI cache to prevent database schema issues..."
if [ -d "/stable-diffusion-webui/cache" ]; then
    rm -rf /stable-diffusion-webui/cache/*
    echo "✓ Cache directory cleaned"
else
    echo "ℹ Cache directory not found, skipping cleanup"
fi

# Clean any existing model cache that might cause issues
if [ -d "/stable-diffusion-webui/models" ]; then
    find /stable-diffusion-webui/models -name "*.cache" -delete 2>/dev/null || true
    echo "✓ Model cache files cleaned"
fi

# Start WebUI API in background with enhanced error handling
echo "🚀 Starting WebUI with enhanced parameters to prevent txt2img endpoint issues..."
cd /stable-diffusion-webui && python webui.py \
  --xformers \
  --no-half-vae \
  --no-half \
  --skip-python-version-check \
  --skip-torch-cuda-test \
  --skip-install \
  --skip-prepare-environment \
  --ckpt-dir /runpod-volume/models/checkpoints \
  --lora-dir /runpod-volume/models/loras \
  --embeddings-dir /runpod-volume/models/embeddings \
  --ckpt /model.safetensors \
  --opt-sdp-attention \
  --disable-safe-unpickle \
  --port 3000 \
  --api \
  --nowebui \
  --skip-version-check \
  --no-hashing \
  --no-download-sd-model \
  --api-log \
  --enable-insecure-extension-access \
  --disable-console-progressbars \
  --no-progressbar-hiding \
  --force-enable-xformers \
  --api-server-stop &

# Store WebUI PID for monitoring
WEBUI_PID=$!
echo "WebUI API started with PID: $WEBUI_PID"

echo ""
echo "=============================================="
echo "STARTING RUNPOD HANDLER"
echo "=============================================="

# Start RunPod handler
python -u ./handler.py

# If handler exits, also stop WebUI
echo "RunPod handler exited, stopping WebUI API..."
kill $WEBUI_PID 2>/dev/null || true
wait $WEBUI_PID 2>/dev/null || true
echo "Shutdown complete."
