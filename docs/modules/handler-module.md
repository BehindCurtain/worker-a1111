# Modül Haritası: Handler Module (handler.py)

## Genel Bakış

Handler modülü, RunPod serverless platform ile Automatic1111 WebUI API arasındaki ana interface'i sağlar. Request processing, service management ve error handling işlevlerini içerir.

## Modül Yapısı

### Import Dependencies
```python
import time
import runpod
import requests
from requests.adapters import HTTPAdapter, Retry
```

### Global Configuration
```python
LOCAL_URL = "http://127.0.0.1:3000/sdapi/v1"
automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))
```

## Fonksiyon Analizi

### 1. wait_for_service(url, max_retries=300)

#### Amaç
WebUI API servisinin hazır olmasını bekler ve service readiness kontrolü yapar.

#### Parametreler
- `url` (string): Kontrol edilecek service endpoint URL'i
- `max_retries` (int): Maksimum retry sayısı (default: 300)

#### İşleyiş
```python
def wait_for_service(url, max_retries=300):
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
            if retries % 15 == 0:
                print(f"Service not ready yet. Retrying... ({retries}/{max_retries})")
        except Exception as err:
            print("Error: ", err)
            retries += 1
        time.sleep(0.2)
    
    raise Exception(f"Service at {url} failed to start after {max_retries} retries ({max_retries * 0.2} seconds)")
```

#### Özellikler
- **Status Code Validation**: 200 OK kontrolü
- **Timeout**: 120 saniye request timeout
- **Retry Limit**: Maksimum 300 retry (60 saniye)
- **Progress Logging**: Her 15 retry'da bir progress log
- **Sleep Interval**: 0.2 saniye bekleme süresi
- **Error Handling**: Generic exception handling
- **Timeout Exception**: Max retry aşımında exception fırlatma

#### Kullanım Senaryoları
- Container startup sırasında WebUI API hazırlık kontrolü
- Service health check operations
- Dependency service validation
- Infinite loop prevention

### 1.1. wait_for_txt2img_service(max_retries=240)

#### Amaç
txt2img endpoint'inin özellikle hazır olmasını bekler ve 404 hatalarını önler.

#### Parametreler
- `max_retries` (int): Maksimum retry sayısı (default: 240)

#### İşleyiş
```python
def wait_for_txt2img_service(max_retries=240):
    print("Checking txt2img endpoint availability...")
    retries = 0
    
    while retries < max_retries:
        try:
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
    
    raise Exception(f"txt2img endpoint failed to start after {max_retries} retries ({max_retries * 0.5} seconds)")
```

#### Özellikler
- **Endpoint Specific Check**: txt2img endpoint'i özel kontrolü
- **Minimal Test Request**: Küçük test isteği ile endpoint varlığı kontrolü
- **404 Detection**: 404 hatalarını özel olarak handle eder
- **Ready State Detection**: 200, 400, 422 status kodlarını "hazır" kabul eder
- **Timeout**: 30 saniye test request timeout
- **Retry Limit**: Maksimum 240 retry (120 saniye)
- **Progress Logging**: Her 15 retry'da bir progress log
- **Timeout Exception**: Max retry aşımında exception fırlatma

### 1.2. check_model_status()

#### Amaç
Mevcut model durumunu kontrol eder ve kullanılabilir modelleri listeler.

#### Parametreler
- Parametre almaz

#### Return
- `bool`: Model durumu kontrolü başarılı ise True

#### İşleyiş
```python
def check_model_status():
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
            for model in models[:3]:
                print(f"  - {model.get('title', 'Unknown')}")
            return True
```

#### Özellikler
- **Current Model Detection**: Aktif model bilgisi
- **Available Models List**: Kullanılabilir modeller listesi
- **Model Count**: Toplam model sayısı
- **Sample Display**: İlk 3 model'i örnek olarak gösterir
- **Error Tolerance**: Hata durumunda False döndürür

### 2. run_inference(inference_request)

#### Amaç
Automatic1111 WebUI API'sine inference request gönderir ve response alır (404 error recovery ile)

#### Parametreler
- `inference_request` (dict): txt2img API için request parametreleri

#### İşleyiş
```python
def run_inference(inference_request):
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = automatic_session.post(url=f'{LOCAL_URL}/txt2img',
                                              json=inference_request, timeout=600)
            
            if response.status_code == 200:
                result = response.json()
                print("✓ Inference completed successfully")
                return result
            elif response.status_code == 404:
                # Recovery mechanism for 404 errors
                if attempt < max_retries - 1:
                    print(f"🔄 Attempting recovery... waiting {retry_delay} seconds")
                    time.sleep(retry_delay)
                    
                    # Try to recover by checking API health
                    wait_for_service(url=f'{LOCAL_URL}/sd-models', max_retries=60)
                    check_model_status()
                    wait_for_txt2img_service(max_retries=60)
                    continue
```

#### Özellikler
- **Enhanced Logging**: Detaylı request ve response logging
- **Status Code Validation**: HTTP status code kontrolü
- **404 Error Recovery**: 404 hatalarında otomatik recovery mekanizması
- **Multi-Attempt Strategy**: 3 deneme ile 5 saniye delay
- **API Health Recovery**: Service readiness re-check
- **Model Status Verification**: Post-recovery model kontrolü
- **Error Diagnostics**: Hata durumunda detaylı bilgi sağlar
- **Session Reuse**: Global session object kullanımı
- **Long Timeout**: 600 saniye timeout (image generation için)
- **Exception Handling**: Timeout, connection ve HTTP errors

#### Enhanced Recovery Mechanism
1. **404 Detection**: txt2img endpoint not found
2. **Recovery Wait**: 5 saniye bekleme
3. **Cache Cleanup**: SQLite cache database cleanup to resolve schema issues
4. **API Health Check**: Basic service readiness kontrolü
5. **Model Status Check**: Model availability verification
6. **txt2img Check**: Endpoint-specific readiness kontrolü with extended timeout
7. **Retry Attempt**: Recovered service ile yeniden deneme

#### Cache Cleanup Function
```python
def clean_webui_cache():
    """Clean WebUI cache to resolve SQLite schema issues."""
    import os
    import shutil
    
    cache_paths = [
        "/stable-diffusion-webui/cache",
        "/stable-diffusion-webui/models/Stable-diffusion/*.cache",
        "/stable-diffusion-webui/models/Lora/*.cache"
    ]
    
    print("🧹 Cleaning WebUI cache to resolve database issues...")
    
    for cache_path in cache_paths:
        try:
            if "*" in cache_path:
                import glob
                for file_path in glob.glob(cache_path):
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"✓ Removed cache file: {file_path}")
            else:
                if os.path.exists(cache_path):
                    shutil.rmtree(cache_path)
                    print(f"✓ Cleaned cache directory: {cache_path}")
                    os.makedirs(cache_path, exist_ok=True)
        except Exception as e:
            print(f"⚠ Warning: Could not clean {cache_path}: {e}")
    
    print("✓ Cache cleanup completed")
```

#### Error Handling
- **404 Errors**: Automatic recovery mechanism
- **Timeout Errors**: Multi-attempt retry strategy
- **Connection Errors**: Retry with delay
- **HTTP Errors**: Standard error propagation

#### Request Flow
1. **Multi-Attempt Loop**: 3 deneme ile retry logic
2. **Request Logging**: Request parametrelerini logla
3. **HTTP POST**: Session-based request execution
4. **Status Validation**: HTTP status code kontrolü
5. **Recovery Logic**: 404 durumunda recovery sequence
6. **Success Handling**: 200 OK durumunda JSON parse
7. **Error Handling**: Hata durumlarında detaylı logging

### 3. prepare_inference_request(input_data)

#### Amaç
Input data'yı WebUI API format'ına dönüştürür ve model management entegrasyonu sağlar.

#### Parametreler
- `input_data` (dict): RunPod event'inden gelen raw input data

#### Return
- `dict`: WebUI API için hazırlanmış inference request

#### İşleyiş
```python
def prepare_inference_request(input_data):
    # Extract model information
    checkpoint_info = input_data.get("checkpoint")
    loras = input_data.get("loras", [])
    
    # Prepare models (download if needed)
    checkpoint_path, lora_paths, models_downloaded = model_manager.prepare_models_for_request(
        checkpoint_info, loras
    )
    
    # If new models were downloaded, wait for WebUI API to recognize them
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
        print(f"Using checkpoint: {checkpoint_info['name']} at {checkpoint_path}")
        
        if "override_settings" not in inference_request:
            inference_request["override_settings"] = {}
        
        inference_request["override_settings"]["sd_model_checkpoint"] = checkpoint_info["name"]
    
    return inference_request
```

#### Özellikler
- **Model Management Integration**: model_manager ile entegrasyon
- **LoRA Support**: LoRA model'leri otomatik download ve prompt enhancement
- **Checkpoint Handling**: Checkpoint switching desteği
- **Parameter Mapping**: Standard parametreleri otomatik kopyalama
- **CLIP Skip Support**: clip_skip parametresi desteği
- **Override Settings**: WebUI API override_settings kullanımı
- **Model Download Detection**: Yeni model indirme durumu takibi
- **API Stability Check**: Model indirme sonrası API sağlık kontrolü
- **Registry Update Wait**: Model registry güncellemesi için bekleme
- **Graceful Degradation**: Sağlık kontrolü başarısız olsa bile devam etme

#### Supported Parameters
- **Basic**: prompt, negative_prompt, steps, cfg_scale, width, height
- **Advanced**: sampler_name, seed, batch_size, n_iter, clip_skip
- **Options**: restore_faces, tiling, do_not_save_samples, do_not_save_grid
- **Models**: checkpoint (object), loras (array)

### 4. handler(event)

#### Amaç
RunPod serverless platform için ana entry point fonksiyonu.

#### Parametreler
- `event` (dict): RunPod event object containing input data

#### Return
- `dict`: Inference result with cache info

#### İşleyiş
```python
def handler(event):
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
```

#### Özellikler
- **Enhanced Error Handling**: Try-catch ile error handling
- **Model Management**: prepare_inference_request entegrasyonu
- **Cache Statistics**: Response'a cache bilgisi ekleme
- **Debug Information**: Cache stats ile debugging desteği
- **Error Response**: Standardized error response format

#### Integration Points
- **RunPod Platform**: Serverless event handling
- **Model Manager**: Model download ve management
- **Inference Engine**: WebUI API integration
- **Cache System**: Model cache statistics

## Startup Sequence

### Main Function (__main__)

#### Amaç
WebUI API'nin tam olarak hazır olmasını sağlayan multi-step startup sequence.

#### İşleyiş
```python
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
```

#### Startup Steps
1. **Basic API Check**: `/sd-models` endpoint readiness
2. **Model Status Check**: Current model ve available models kontrolü
3. **txt2img Endpoint Check**: txt2img endpoint'i özel kontrolü
4. **RunPod Start**: Serverless handler başlatma

#### Error Handling
- **Model Status Failure**: Warning ile devam eder
- **API Service Failure**: Timeout sonrası exception
- **txt2img Failure**: Timeout sonrası exception
- **Fatal Errors**: Container exit ile graceful shutdown
- **Error Diagnostics**: Detaylı hata mesajları ve troubleshooting ipuçları

## Modül İlişkileri

### Internal Dependencies
- **wait_for_service**: Service readiness validation
- **wait_for_txt2img_service**: txt2img endpoint validation
- **check_model_status**: Model status validation
- **prepare_inference_request**: Request preparation
- **run_inference**: Core inference processing
- **handler**: Platform integration layer

### External Dependencies
- **runpod**: Serverless platform SDK
- **requests**: HTTP client library
- **time**: Sleep ve timing operations
- **model_manager**: Model download ve management

### Data Flow
```
RunPod Event → handler() → prepare_inference_request() → run_inference() → WebUI API
                ↓                        ↓                      ↓
RunPod Response ← Cache Info ← Model Management ← JSON Response ← HTTP Response
```

## Configuration Management

### Global Variables
- **LOCAL_URL**: WebUI API base URL
- **automatic_session**: Persistent HTTP session
- **retries**: Retry policy configuration

### Session Configuration
```python
retries = Retry(
    total=10,                    # Maximum retry attempts
    backoff_factor=0.1,          # Exponential backoff multiplier
    status_forcelist=[502, 503, 504]  # HTTP status codes to retry
)
```

### Timeout Configuration
- **Service Check**: 120 seconds
- **Inference Request**: 600 seconds
- **Retry Interval**: 0.2 seconds

## Error Handling Strategy

### Service Readiness Errors
- **Network Errors**: Continuous retry with logging
- **Timeout Errors**: Automatic retry mechanism
- **Generic Errors**: Error logging with continuation

### Inference Errors
- **HTTP Errors**: Automatic retry through session configuration
- **Timeout Errors**: 600 second timeout for complex generations
- **JSON Errors**: Propagated to caller

### Logging Strategy
- **Service Status**: Periodic readiness logging
- **Error Conditions**: Exception logging
- **Minimal Logging**: Spam prevention through interval logging

## Performance Characteristics

### Connection Management
- **Session Reuse**: HTTP connection pooling
- **Keep-Alive**: Persistent connections
- **Retry Logic**: Intelligent retry with backoff

### Memory Usage
- **Stateless Processing**: No request data persistence
- **Session Caching**: HTTP session object reuse
- **Minimal Memory Footprint**: Efficient request handling

### Latency Optimization
- **Connection Pooling**: Reduced connection overhead
- **Direct Passthrough**: Minimal processing overhead
- **Efficient Serialization**: JSON handling optimization

## Integration Patterns

### RunPod Integration
- **Event-Driven**: Serverless event processing
- **Stateless**: No persistent state management
- **JSON Communication**: Standardized data format

### WebUI API Integration
- **REST API**: HTTP-based communication
- **JSON Payload**: Structured data exchange
- **Session Management**: Persistent connection handling

## Monitoring ve Observability

### Logging Points
- **Service Readiness**: Startup sequence logging
- **Error Conditions**: Exception ve retry logging
- **Performance Metrics**: Implicit through platform

### Health Indicators
- **Service Status**: wait_for_service success/failure
- **Request Success**: HTTP response status
- **Response Time**: Request duration metrics

## Troubleshooting

### Common Issues
1. **Service Not Ready**: WebUI startup delays
2. **Connection Timeouts**: Network or processing issues
3. **JSON Parsing Errors**: Malformed API responses
4. **Memory Issues**: Large request processing

### Debug Strategies
- **Service Logs**: wait_for_service retry logging
- **Request Tracing**: HTTP request/response analysis
- **Error Analysis**: Exception stack trace review
- **Performance Profiling**: Request timing analysis

## Optimizasyon Fırsatları

### Performance Improvements
- **Async Processing**: Asynchronous request handling
- **Request Batching**: Multiple request optimization
- **Response Caching**: Selective caching strategies
- **Connection Tuning**: HTTP client optimization

### Reliability Enhancements
- **Circuit Breaker**: Failure detection ve recovery
- **Health Monitoring**: Proactive service monitoring
- **Graceful Degradation**: Fallback mechanisms
- **Request Validation**: Input parameter validation

Bu modül, projenin core functionality'sini sağlar ve tüm API communication'ın reliable şekilde gerçekleşmesini garanti eder.
