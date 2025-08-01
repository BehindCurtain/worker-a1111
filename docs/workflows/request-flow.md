# İş Süreci: Request Flow

## Genel Bakış

Request Flow, bir RunPod API isteğinin alınmasından görsel üretiminin tamamlanmasına kadar olan end-to-end süreçtir. Bu workflow, tüm sistem bileşenlerinin koordineli çalışmasını ve veri akışını tanımlar.

## Süreç Adımları

### 1. Request Reception
**Sorumlu Bileşen**: RunPod Platform
**Süre**: < 100ms

#### İşleyiş
- RunPod platform'dan serverless event alınır
- Event validation ve routing yapılır
- Handler function'a event iletilir

#### Veri Yapısı
```json
{
  "input": {
    "prompt": "a photograph of an astronaut riding a horse",
    "negative_prompt": "text, watermark, blurry, low quality",
    "steps": 25,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
    "sampler_name": "DPM++ 2M Karras"
  }
}
```

#### Kritik Noktalar
- Event format validation
- Input parameter extraction
- Handler function invocation

### 2. Handler Processing
**Sorumlu Bileşen**: handler.py - handler() function
**Süre**: < 10ms

#### İşleyiş
```python
def handler(event):
    json = run_inference(event["input"])
    return json
```

#### Veri Akışı
1. **Event Parsing**: RunPod event structure'dan input extraction
2. **Parameter Forwarding**: Input parametrelerini run_inference'a iletme
3. **Response Handling**: Inference sonucunu doğrudan döndürme

#### Hata Senaryoları
- Malformed event structure
- Missing input field
- Invalid parameter types

### 3. Service Readiness Check
**Sorumlu Bileşen**: handler.py - wait_for_service() function
**Süre**: 0-60 seconds (startup'da)

#### İşleyiş
```python
def wait_for_service(url):
    while True:
        try:
            requests.get(url, timeout=120)
            return
        except:
            time.sleep(0.2)
```

#### Kontrol Mekanizması
- **Health Endpoint**: http://127.0.0.1:3000/sdapi/v1/sd-models
- **Polling Interval**: 0.2 seconds
- **Timeout**: 120 seconds per request
- **Retry Strategy**: Infinite loop until success

#### Service States
- **Not Ready**: WebUI API henüz başlatılmamış
- **Starting**: WebUI API initialization süreci
- **Ready**: API requests kabul etmeye hazır

### 4. Model Preparation & Hardcoded Checkpoint Management
**Sorumlu Bileşen**: handler.py - prepare_inference_request() function
**Süre**: 0-300 seconds (model download dependent)

#### İşleyiş
```python
def prepare_inference_request(input_data):
    # 1. Validate request (no checkpoint validation needed - it's hardcoded)
    validate_request(input_data)
    
    # 2. Use hardcoded checkpoint and extract LoRAs from request
    checkpoint_info = HARDCODED_CHECKPOINT
    loras = input_data.get("loras", [])
    
    print(f"🎯 Using hardcoded checkpoint: {checkpoint_info['name']}")
    
    # 3. Prepare models (download if needed)
    checkpoint_path, lora_paths, models_downloaded = model_manager.prepare_models_for_request(
        checkpoint_info, loras
    )
    
    # 4. Handle checkpoint switching
    if checkpoint_info:
        current_model = get_current_model()
        target_checkpoint = checkpoint_info["name"]
        
        if target_checkpoint not in current_model:
            change_checkpoint(target_checkpoint)
            wait_for_model_loading()
            verify_checkpoint_loaded(target_checkpoint)
```

#### Hardcoded Checkpoint Yönetimi
1. **Request Validation**: Sadece prompt kontrolü (checkpoint hardcoded)
2. **Hardcoded Checkpoint**: Her zaman "Jib Mix Illustrious Realistic" kullanılır
3. **Current Model Check**: Mevcut yüklü model kontrolü
4. **Checkpoint Switching**: API-based model değişimi (gerekirse)
5. **Loading Monitor**: Progress endpoint ile takip
6. **Verification**: Model değişiminin doğrulanması

#### Model Management
1. **Cache Check**: Verify if models are already cached
2. **Download Process**: Download missing models from CivitAI
3. **Registry Update**: Update model cache registry
4. **API Stability**: Verify WebUI API health after downloads

#### Checkpoint Değişim Süreci
- **Current Model Detection**: WebUI API'den mevcut model bilgisi
- **Target Comparison**: Hedef checkpoint ile karşılaştırma
- **API Request**: `/sdapi/v1/options` endpoint ile değişim
- **Progress Monitoring**: `/sdapi/v1/progress` ile takip
- **Verification**: Model değişiminin başarılı olduğunu doğrulama
- **Error Handling**: Başarısızlık durumunda exception

#### Download Impact Handling
- **New Model Detection**: Track when models are downloaded
- **API Health Check**: Verify service stability post-download
- **Registry Sync**: 3-second wait for model registry updates
- **Graceful Degradation**: Continue with warnings if checks fail

### 5. Inference Request
**Sorumlu Bileşen**: handler.py - run_inference() function
**Süre**: 10-120 seconds

#### İşleyiş
```python
def run_inference(inference_request):
    for attempt in range(max_retries):
        response = automatic_session.post(
            url=f'{LOCAL_URL}/txt2img',
            json=inference_request, 
            timeout=600
        )
        if response.status_code == 404:
            # Recovery mechanism
            wait_for_service(url=f'{LOCAL_URL}/sd-models')
            wait_for_txt2img_service()
```

#### HTTP Request Details
- **Method**: POST
- **URL**: http://127.0.0.1:3000/sdapi/v1/txt2img
- **Content-Type**: application/json
- **Timeout**: 600 seconds
- **Retry Policy**: 3 attempts with 5-second delays
- **Recovery Mechanism**: Automatic API health recovery on 404 errors

#### Request Processing
1. **Session Reuse**: HTTP connection pooling
2. **JSON Serialization**: Automatic parameter encoding
3. **Request Transmission**: HTTP POST to WebUI API
4. **Response Reception**: JSON response parsing
5. **Error Recovery**: 404 error recovery with API health checks

### 5. AI Processing
**Sorumlu Bileşen**: Automatic1111 WebUI API
**Süre**: 10-120 seconds (complexity dependent)

#### Processing Pipeline
1. **Prompt Processing**: Text encoding ve tokenization
2. **Noise Generation**: Random noise tensor creation
3. **Denoising Steps**: Iterative noise reduction (steps parameter)
4. **VAE Decoding**: Latent space to image conversion
5. **Post-processing**: Image formatting ve metadata

#### Resource Utilization
- **GPU Memory**: ~4-6GB (model + inference buffer)
- **Processing Time**: Steps ve resolution dependent
- **CPU Usage**: Minimal (GPU-accelerated processing)

#### Quality Factors
- **Steps**: Denoising iteration count (quality vs speed)
- **CFG Scale**: Prompt adherence strength
- **Sampler**: Algorithm selection impact
- **Resolution**: Output image dimensions

### 6. Response Generation
**Sorumlu Bileşen**: Automatic1111 WebUI API
**Süre**: < 1 second

#### Response Structure
```json
{
  "images": ["base64_encoded_image_data"],
  "parameters": {
    "prompt": "original_prompt",
    "steps": 25,
    "cfg_scale": 7,
    "width": 512,
    "height": 512,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 1234567890
  },
  "info": "generation_metadata"
}
```

#### Response Components
- **Images**: Base64 encoded PNG data
- **Parameters**: Used generation parameters
- **Info**: Metadata ve generation details
- **Seed**: Reproducibility information

### 7. Response Forwarding
**Sorumlu Bileşen**: handler.py - run_inference() return
**Süre**: < 10ms

#### İşleyiş
- WebUI API response'u JSON olarak parse edilir
- Response doğrudan handler function'a döndürülür
- Handler response'u RunPod platform'a iletir

#### Data Passthrough
- **No Processing**: Response modification yapılmaz
- **Direct Forward**: API response olduğu gibi iletilir
- **Error Propagation**: API errors client'a yansıtılır

### 8. Platform Response
**Sorumlu Bileşen**: RunPod Platform
**Süre**: < 100ms

#### Final Processing
- Handler response RunPod format'ına wrap edilir
- Client'a HTTP response olarak iletilir
- Request lifecycle tamamlanır

## Veri Akış Diyagramı

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RunPod        │    │    Handler       │    │   WebUI API     │
│   Platform      │    │    Service       │    │   Service       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. Event              │                       │
         ├──────────────────────►│                       │
         │                       │ 2. Service Check      │
         │                       ├──────────────────────►│
         │                       │ 3. Ready Response     │
         │                       │◄──────────────────────┤
         │                       │ 4. Inference Request  │
         │                       ├──────────────────────►│
         │                       │                       │ 5. AI Processing
         │                       │                       │ (10-120 seconds)
         │                       │ 6. Generated Response │
         │                       │◄──────────────────────┤
         │ 7. Final Response     │                       │
         │◄──────────────────────┤                       │
         │                       │                       │
```

## Performance Metrikleri

### Latency Breakdown
- **Platform Overhead**: ~200ms (request + response)
- **Handler Processing**: ~20ms (parsing + forwarding)
- **Service Check**: 0ms (cached after startup)
- **AI Processing**: 10-120 seconds (dominant factor)
- **Total Latency**: 10-120 seconds + ~220ms overhead

### Throughput Characteristics
- **Sequential Processing**: One request at a time
- **GPU Bound**: Processing speed GPU performance dependent
- **Memory Limited**: VRAM capacity constrains batch size
- **Quality Trade-off**: Steps vs speed optimization

## Error Handling

### Error Propagation Chain
```
WebUI API Error → HTTP Response → run_inference() → handler() → RunPod Platform
```

### Common Error Scenarios

#### 1. Service Not Ready
- **Cause**: WebUI API not initialized
- **Handling**: wait_for_service() polling
- **Recovery**: Automatic retry until ready

#### 2. Invalid Parameters
- **Cause**: Malformed input parameters
- **Handling**: WebUI API validation
- **Response**: HTTP 400 with error details

#### 3. GPU Memory Exhaustion
- **Cause**: Large image generation request
- **Handling**: WebUI API error response
- **Recovery**: Request parameter adjustment needed

#### 4. Generation Timeout
- **Cause**: Complex prompt or high step count
- **Handling**: 600 second timeout
- **Recovery**: Request retry with reduced complexity

### Retry Mechanisms

#### HTTP Level Retries
- **Total Attempts**: 10
- **Backoff Factor**: 0.1 (exponential)
- **Status Codes**: 502, 503, 504
- **Timeout**: 600 seconds per attempt

#### Service Level Retries
- **Health Check**: Continuous polling
- **Interval**: 0.2 seconds
- **Logging**: Every 15 attempts

## Monitoring Points

### Request Tracking
1. **Request Reception**: RunPod event timestamp
2. **Handler Start**: Processing initiation
3. **Service Check**: Readiness validation
4. **Inference Start**: WebUI API request
5. **Processing Complete**: Response generation
6. **Response Sent**: Final response delivery

### Performance Metrics
- **End-to-End Latency**: Total request processing time
- **AI Processing Time**: Core generation duration
- **Queue Time**: Service readiness wait time
- **Error Rate**: Failed request percentage

### Health Indicators
- **Service Availability**: WebUI API uptime
- **Response Success Rate**: Successful generation percentage
- **Average Processing Time**: Performance trend tracking
- **Resource Utilization**: GPU ve memory usage

## Optimizasyon Fırsatları

### Latency Reduction
- **Model Caching**: Persistent VRAM storage
- **Parameter Optimization**: Default value tuning
- **Connection Pooling**: HTTP session reuse
- **Batch Processing**: Multiple request handling

### Throughput Improvement
- **Parallel Processing**: Multi-GPU support
- **Queue Management**: Request batching
- **Resource Scaling**: Dynamic resource allocation
- **Cache Strategies**: Response caching for similar requests

Bu workflow, projenin core functionality'sinin end-to-end işleyişini tanımlar ve tüm bileşenlerin koordineli çalışmasını sağlar.
