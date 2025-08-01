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

# Start WebUI API in background
cd /stable-diffusion-webui && python webui.py \
  --xformers \
  --no-half-vae \
  --skip-python-version-check \
  --skip-torch-cuda-test \
  --skip-install \
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
  --no-download-sd-model &

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
