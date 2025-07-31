<h1>Automatic1111 Stable Diffusion web UI</h1>

[![RunPod](https://api.runpod.io/badge/runpod-workers/worker-a1111)](https://www.runpod.io/console/hub/runpod-workers/worker-a1111)

- Runs [Automatic1111 Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) and exposes its `txt2img` API endpoint
- Comes pre-packaged with the [**Deliberate v6**](https://huggingface.co/XpucT/Deliberate) model

---

## Usage

The `input` object accepts any valid parameter for the Automatic1111 `/sdapi/v1/txt2img` endpoint, plus additional support for dynamic checkpoint and LoRA loading. Refer to the [Automatic1111 API Documentation](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API) for a full list of available parameters.

### Enhanced Features

- **Dynamic Checkpoint Loading**: Load different Stable Diffusion models on-demand
- **LoRA Support**: Apply LoRA models with custom scales
- **Network Volume Caching**: Persistent model storage across container restarts
- **Automatic Model Management**: Download, cache, and verify model integrity

### Example Request

Here's an example payload to generate an image with LoRA support:

```json
{
  "input": {
    "prompt": "a beautiful landscape with mountains and lake",
    "negative_prompt": "blurry, bad quality, low resolution",
    "steps": 25,
    "cfg_scale": 7.5,
    "width": 512,
    "height": 512,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 42,
    "checkpoint": {
      "name": "deliberate_v6",
      "url": "https://huggingface.co/XpucT/Deliberate/resolve/main/Deliberate_v6.safetensors",
      "hash": "optional_sha256_hash_for_verification"
    },
    "loras": [
      {
        "name": "landscape_enhancer",
        "url": "https://civitai.com/api/download/models/12345",
        "scale": 0.8,
        "hash": "optional_sha256_hash_for_verification"
      },
      {
        "name": "detail_tweaker",
        "url": "https://huggingface.co/user/model/resolve/main/model.safetensors",
        "scale": 0.5
      }
    ]
  }
}
```

### Network Volume Setup

To enable persistent model caching, mount a RunPod Network Volume to `/workspace/models`:

```bash
# RunPod Network Volume structure
/workspace/models/
├── checkpoints/     # Stable Diffusion checkpoints
├── loras/          # LoRA models
├── embeddings/     # Textual inversions
└── cache_registry.json  # Model metadata cache
```

### Response Format

The response includes the standard Automatic1111 output plus cache information:

```json
{
  "images": ["base64_encoded_image_data"],
  "parameters": {
    "prompt": "<lora:landscape_enhancer:0.8> a beautiful landscape...",
    "steps": 25,
    "cfg_scale": 7.5,
    // ... other parameters
  },
  "info": "generation_metadata",
  "cache_info": {
    "checkpoints_cached": 3,
    "loras_cached": 15,
    "total_cache_size_mb": 2048.5
  }
}
```
