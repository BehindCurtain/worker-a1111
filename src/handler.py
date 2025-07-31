import time
import runpod
import requests
from requests.adapters import HTTPAdapter, Retry
from model_manager import model_manager

LOCAL_URL = "http://127.0.0.1:3000/sdapi/v1"

automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))


# ---------------------------------------------------------------------------- #
#                              Automatic Functions                             #
# ---------------------------------------------------------------------------- #
def wait_for_service(url):
    """
    Check if the service is ready to receive requests.
    """
    retries = 0

    while True:
        try:
            requests.get(url, timeout=120)
            return
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 15 == 0:
                print("Service not ready yet. Retrying...")
        except Exception as err:
            print("Error: ", err)

        time.sleep(0.2)


def run_inference(inference_request):
    """
    Run inference on a request.
    """
    response = automatic_session.post(url=f'{LOCAL_URL}/txt2img',
                                      json=inference_request, timeout=600)
    return response.json()


def prepare_inference_request(input_data):
    """
    Prepare inference request with model management and LoRA support.
    """
    # Extract model information
    checkpoint_info = input_data.get("checkpoint")
    loras = input_data.get("loras", [])
    
    # Prepare models (download if needed)
    checkpoint_path, lora_paths = model_manager.prepare_models_for_request(
        checkpoint_info, loras
    )
    
    # Build the inference request
    inference_request = {}
    
    # Copy standard parameters
    standard_params = [
        "prompt", "negative_prompt", "steps", "cfg_scale", "width", "height",
        "sampler_name", "seed", "batch_size", "n_iter", "restore_faces",
        "tiling", "do_not_save_samples", "do_not_save_grid"
    ]
    
    for param in standard_params:
        if param in input_data:
            inference_request[param] = input_data[param]
    
    # Handle prompt with LoRA integration
    base_prompt = input_data.get("prompt", "")
    if lora_paths:
        enhanced_prompt = model_manager.build_lora_prompt(base_prompt, lora_paths)
        inference_request["prompt"] = enhanced_prompt
        print(f"Enhanced prompt with LoRAs: {enhanced_prompt}")
    
    # Handle checkpoint switching if needed
    if checkpoint_path and checkpoint_info:
        # Note: Checkpoint switching requires WebUI API restart or model reload
        # For now, we'll log the checkpoint info
        print(f"Using checkpoint: {checkpoint_info['name']} at {checkpoint_path}")
        
        # Add checkpoint info to override_settings if supported
        if "override_settings" not in inference_request:
            inference_request["override_settings"] = {}
        
        # Try to set the checkpoint (this may not work without WebUI restart)
        inference_request["override_settings"]["sd_model_checkpoint"] = checkpoint_info["name"]
    
    return inference_request


# ---------------------------------------------------------------------------- #
#                                RunPod Handler                                #
# ---------------------------------------------------------------------------- #
def handler(event):
    """
    This is the handler function that will be called by the serverless.
    """
    try:
        # Prepare inference request with model management
        inference_request = prepare_inference_request(event["input"])
        
        # Run inference
        result = run_inference(inference_request)
        
        # Add cache statistics to response for debugging
        cache_stats = model_manager.get_cache_stats()
        result["cache_info"] = {
            "checkpoints_cached": cache_stats["checkpoints"]["count"],
            "loras_cached": cache_stats["loras"]["count"],
            "total_cache_size_mb": (cache_stats["checkpoints"]["total_size"] + 
                                  cache_stats["loras"]["total_size"]) / (1024 * 1024)
        }
        
        return result
        
    except Exception as e:
        print(f"Error in handler: {e}")
        return {
            "error": str(e),
            "message": "Failed to process inference request"
        }


if __name__ == "__main__":
    wait_for_service(url=f'{LOCAL_URL}/sd-models')
    print("WebUI API Service is ready. Starting RunPod Serverless...")
    runpod.serverless.start({"handler": handler})
