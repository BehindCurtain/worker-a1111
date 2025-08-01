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
def wait_for_service(url, max_retries=300):
    """
    Check if the service is ready to receive requests.
    """
    retries = 0

    while retries < max_retries:
        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 200:
                return
            else:
                print(f"Service returned status {response.status_code}, retrying...")
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 15 == 0:
                print(f"Service not ready yet. Retrying... ({retries}/{max_retries})")
        except Exception as err:
            print("Error: ", err)
            retries += 1

        time.sleep(0.2)
    
    # If we reach here, service didn't start within timeout
    raise Exception(f"Service at {url} failed to start after {max_retries} retries ({max_retries * 0.2} seconds)")


def wait_for_txt2img_service(max_retries=240):
    """
    Check if the txt2img endpoint is ready to receive requests.
    """
    print("Checking txt2img endpoint availability...")
    retries = 0
    
    while retries < max_retries:
        try:
            # Test with a minimal request to see if endpoint exists
            test_request = {
                "prompt": "test",
                "steps": 1,
                "width": 64,
                "height": 64
            }
            response = automatic_session.post(
                url=f'{LOCAL_URL}/txt2img',
                json=test_request,
                timeout=30
            )
            
            # If we get any response (even error), endpoint exists
            if response.status_code in [200, 400, 422]:
                print("txt2img endpoint is ready")
                return
            elif response.status_code == 404:
                retries += 1
                if retries % 15 == 0:
                    print(f"txt2img endpoint not found (404), retrying... ({retries}/{max_retries})")
            else:
                print(f"txt2img endpoint returned status {response.status_code}, retrying...")
                retries += 1
                
        except requests.exceptions.RequestException as e:
            retries += 1
            if retries % 15 == 0:
                print(f"txt2img endpoint not ready: {e} ({retries}/{max_retries})")
        except Exception as err:
            print("Error checking txt2img endpoint: ", err)
            retries += 1

        time.sleep(0.5)
    
    # If we reach here, txt2img endpoint didn't start within timeout
    raise Exception(f"txt2img endpoint failed to start after {max_retries} retries ({max_retries * 0.5} seconds)")


def check_model_status():
    """
    Check current model status and available models.
    """
    try:
        # Get current model info
        response = automatic_session.get(f'{LOCAL_URL}/options', timeout=30)
        if response.status_code == 200:
            options = response.json()
            current_model = options.get('sd_model_checkpoint', 'Unknown')
            print(f"Current model: {current_model}")
            
        # Get available models
        response = automatic_session.get(f'{LOCAL_URL}/sd-models', timeout=30)
        if response.status_code == 200:
            models = response.json()
            print(f"Available models: {len(models)} models found")
            for model in models[:3]:  # Show first 3 models
                print(f"  - {model.get('title', 'Unknown')}")
            return True
        else:
            print(f"Failed to get model list: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error checking model status: {e}")
        return False


def run_inference(inference_request):
    """
    Run inference on a request with recovery mechanism for 404 errors.
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Sending inference request to {LOCAL_URL}/txt2img (attempt {attempt + 1}/{max_retries})")
            print(f"Request parameters: steps={inference_request.get('steps')}, "
                  f"size={inference_request.get('width')}x{inference_request.get('height')}, "
                  f"sampler={inference_request.get('sampler_name')}")
            
            response = automatic_session.post(url=f'{LOCAL_URL}/txt2img',
                                              json=inference_request, timeout=600)
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Inference completed successfully")
                return result
            elif response.status_code == 404:
                print("❌ 404 Error: txt2img endpoint not found")
                print("This usually means:")
                print("  1. WebUI API is not fully initialized")
                print("  2. --api flag is missing from WebUI startup")
                print("  3. Model is not loaded properly")
                print("  4. Model switching caused API restart")
                
                # If this is not the last attempt, try recovery
                if attempt < max_retries - 1:
                    print(f"🔄 Attempting recovery... waiting {retry_delay} seconds")
                    time.sleep(retry_delay)
                    
                    # Try to recover by checking API health and waiting for readiness
                    try:
                        print("🔍 Checking API health after 404 error...")
                        wait_for_service(url=f'{LOCAL_URL}/sd-models', max_retries=60)  # 12 seconds max
                        print("✓ Basic API service recovered")
                        
                        # Check model status
                        model_ready = check_model_status()
                        if model_ready:
                            print("✓ Model status confirmed after recovery")
                        else:
                            print("⚠ Model status unclear, but continuing...")
                        
                        # Wait a bit more for txt2img endpoint to be ready
                        wait_for_txt2img_service(max_retries=60)  # 30 seconds max
                        print("✓ txt2img endpoint recovered")
                        
                        # Continue to next attempt
                        continue
                        
                    except Exception as recovery_error:
                        print(f"❌ Recovery failed: {recovery_error}")
                        if attempt == max_retries - 1:
                            # Last attempt failed, give up
                            break
                        else:
                            # Try one more time without recovery
                            continue
                else:
                    # Last attempt, try to get more info about available endpoints
                    try:
                        info_response = automatic_session.get(f'{LOCAL_URL}/../docs', timeout=10)
                        if info_response.status_code == 200:
                            print("API docs are available, but txt2img endpoint is missing")
                        else:
                            print("API docs are also not available")
                    except:
                        print("Cannot access API documentation")
                
                # If we reach here on last attempt, raise the error
                if attempt == max_retries - 1:
                    raise Exception(f"txt2img endpoint returned 404 after {max_retries} attempts. WebUI API may not be properly initialized.")
                    
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text[:200]}")
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout (600s exceeded)")
            if attempt == max_retries - 1:
                raise Exception("Inference request timed out after 600 seconds")
            else:
                print(f"🔄 Retrying after timeout... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
            if attempt == max_retries - 1:
                raise Exception("Cannot connect to WebUI API service")
            else:
                print(f"🔄 Retrying after connection error... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
                
        except Exception as e:
            print(f"❌ Inference error: {e}")
            if attempt == max_retries - 1:
                raise
            else:
                print(f"🔄 Retrying after error... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
    
    # Should not reach here, but just in case
    raise Exception("All inference attempts failed")


def prepare_inference_request(input_data):
    """
    Prepare inference request with model management and LoRA support.
    """
    # Extract model information
    checkpoint_info = input_data.get("checkpoint")
    loras = input_data.get("loras", [])
    
    # Prepare models (download if needed)
    checkpoint_path, lora_paths, models_downloaded = model_manager.prepare_models_for_request(
        checkpoint_info, loras
    )
    
    # If new models were downloaded, we may need to wait for WebUI API to recognize them
    if models_downloaded:
        print("🔄 New models were downloaded. WebUI API may need time to recognize them.")
        print("⏳ Waiting 3 seconds for model registry update...")
        time.sleep(3)
        
        # Check if WebUI API is still responsive after model downloads
        try:
            print("🔍 Verifying WebUI API health after model downloads...")
            wait_for_service(url=f'{LOCAL_URL}/sd-models', max_retries=30)  # 6 seconds max
            print("✓ WebUI API is responsive after model downloads")
        except Exception as e:
            print(f"⚠ Warning: WebUI API health check failed after model downloads: {e}")
            print("⚠ Continuing anyway, but inference may fail...")
    
    # Build the inference request
    inference_request = {}
    
    # Copy standard parameters
    standard_params = [
        "prompt", "negative_prompt", "steps", "cfg_scale", "width", "height",
        "sampler_name", "seed", "batch_size", "n_iter", "restore_faces",
        "tiling", "do_not_save_samples", "do_not_save_grid", "clip_skip"
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
    print("Starting WebUI API readiness checks...")
    
    try:
        # Step 1: Wait for basic API service
        print("Step 1: Checking basic API service...")
        wait_for_service(url=f'{LOCAL_URL}/sd-models')
        print("✓ Basic API service is ready")
        
        # Step 2: Check model status
        print("Step 2: Checking model status...")
        model_ready = check_model_status()
        if not model_ready:
            print("⚠ Warning: Model status check failed, but continuing...")
        else:
            print("✓ Model status check passed")
        
        # Step 3: Wait for txt2img endpoint
        print("Step 3: Checking txt2img endpoint...")
        wait_for_txt2img_service()
        print("✓ txt2img endpoint is ready")
        
        print("🚀 All WebUI API services are ready. Starting RunPod Serverless...")
        runpod.serverless.start({"handler": handler})
        
    except Exception as e:
        print(f"❌ FATAL ERROR: WebUI API failed to start properly")
        print(f"❌ Error details: {e}")
        print("❌ This usually indicates:")
        print("   1. WebUI API process crashed during startup")
        print("   2. Model loading failed")
        print("   3. CUDA/GPU issues")
        print("   4. Insufficient memory")
        print("❌ Container will exit. Check the logs above for more details.")
        exit(1)
