# İş Süreci: Container Lifecycle

## Genel Bakış

Container Lifecycle, Docker container'ın başlatılmasından sonlandırılmasına kadar olan tüm süreçleri kapsar. Bu workflow, service initialization, runtime management ve graceful shutdown işlemlerini tanımlar.

## Lifecycle Phases

### Phase 1: Container Initialization
**Süre**: 0-5 seconds
**Sorumlu**: Docker Runtime + start.sh

#### 1.1 Container Startup
```bash
docker run --gpus all -p 3000:3000 worker-a1111
```

#### İşleyiş
- Docker runtime container'ı başlatır
- GPU access ve port mapping yapılır
- start.sh script execution başlar

#### Resource Allocation
- **GPU Access**: --gpus all flag ile GPU binding
- **Port Mapping**: 3000:3000 API port exposure
- **Memory**: Container memory limits (platform dependent)
- **CPU**: Container CPU allocation

#### Environment Setup
- **Base Image**: Python 3.10.14-slim
- **Working Directory**: Container root
- **User Context**: Default container user
- **File System**: Container layer mounting

### Phase 2: Environment Configuration
**Süre**: < 1 second
**Sorumlu**: start.sh script

#### 2.1 Worker Initialization
```bash
echo "Worker Initiated"
```

#### 2.2 Memory Optimization Setup
```bash
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
```

#### 2.3 Python Environment
```bash
export PYTHONUNBUFFERED=true
```

#### Configuration Details
- **Memory Allocator**: tcmalloc dynamic detection ve activation
- **Python Buffering**: Output buffering deactivation
- **Environment Variables**: Global environment setup
- **Library Loading**: Dynamic library preloading

#### Validation Points
- **tcmalloc Availability**: Library existence check
- **Environment Export**: Variable setting verification
- **Process Environment**: Inherited environment validation

### Phase 3: WebUI API Service Launch
**Süre**: 30-60 seconds
**Sorumlu**: Automatic1111 WebUI

#### 3.1 Service Announcement
```bash
echo "Starting WebUI API"
```

#### 3.2 WebUI Process Launch
```bash
cd /stable-diffusion-webui && python webui.py \
  --xformers \
  --no-half-vae \
  --skip-python-version-check \
  --skip-torch-cuda-test \
  --skip-install \
  --ckpt /model.safetensors \
  --opt-sdp-attention \
  --disable-safe-unpickle \
  --port 3000 \
  --api \
  --nowebui \
  --skip-version-check \
  --no-hashing \
  --no-download-sd-model &
```

#### Initialization Sequence
1. **Python Environment**: Virtual environment activation
2. **Dependency Loading**: PyTorch, transformers, diffusers
3. **Model Loading**: Deliberate v6 model initialization (~4GB VRAM)
4. **GPU Initialization**: CUDA context setup
5. **API Server**: HTTP server başlatma (port 3000)
6. **Background Process**: & ile background execution

#### Resource Requirements
- **VRAM**: ~4GB for model loading
- **RAM**: ~2-4GB for dependencies
- **CPU**: Model loading ve initialization
- **Disk I/O**: Model file reading

#### Critical Dependencies
- **Model File**: /model.safetensors availability
- **GPU Drivers**: CUDA compatibility
- **Python Packages**: Pre-installed dependencies
- **System Libraries**: GPU support libraries

### Phase 4: Handler Service Launch
**Süre**: < 5 seconds
**Sorumlu**: handler.py

#### 4.1 Handler Announcement
```bash
echo "Starting RunPod Handler"
```

#### 4.2 Handler Process Start
```bash
python -u /handler.py
```

#### 4.3 Service Readiness Check
```python
wait_for_service(url=f'{LOCAL_URL}/sd-models')
```

#### 4.4 RunPod Integration
```python
runpod.serverless.start({"handler": handler})
```

#### Initialization Flow
1. **Handler Import**: Module loading ve dependency resolution
2. **Service Check**: WebUI API readiness polling
3. **RunPod Registration**: Serverless handler registration
4. **Event Loop**: Request handling loop başlatma

#### Readiness Validation
- **Health Endpoint**: /sd-models endpoint availability
- **Response Validation**: HTTP 200 status check
- **Retry Logic**: 0.2 second intervals ile continuous polling
- **Timeout Handling**: 120 second per request timeout

### Phase 5: Runtime Operation
**Süre**: Variable (request dependent)
**Sorumlu**: Handler + WebUI API

#### 5.1 Request Processing
- **Event Reception**: RunPod platform events
- **Request Routing**: Handler → WebUI API
- **AI Processing**: Image generation
- **Response Delivery**: Result return

#### 5.2 Resource Management
- **Memory Monitoring**: RAM ve VRAM usage tracking
- **GPU Utilization**: Processing load management
- **Connection Pooling**: HTTP session management
- **Error Handling**: Failure recovery mechanisms

#### 5.3 Health Monitoring
- **Service Status**: Continuous health checks
- **Performance Metrics**: Latency ve throughput tracking
- **Error Rates**: Failure percentage monitoring
- **Resource Alerts**: Threshold-based notifications

### Phase 6: Graceful Shutdown
**Süre**: 5-30 seconds
**Sorumlu**: Docker Runtime + Signal Handlers

#### 6.1 Shutdown Signal Reception
```bash
# SIGTERM signal from Docker
kill -TERM <container_pid>
```

#### 6.2 Service Cleanup
1. **Request Completion**: In-flight requests finish
2. **Connection Cleanup**: HTTP connections close
3. **Resource Release**: GPU memory cleanup
4. **Process Termination**: Service processes stop

#### 6.3 Container Termination
- **Process Tree**: Child process cleanup
- **File System**: Temporary file cleanup
- **Network**: Port binding release
- **GPU**: CUDA context cleanup

## State Transitions

### Container States
```
CREATED → STARTING → CONFIGURING → LAUNCHING → READY → RUNNING → STOPPING → STOPPED
```

#### State Descriptions
- **CREATED**: Container instance created
- **STARTING**: start.sh script execution
- **CONFIGURING**: Environment setup phase
- **LAUNCHING**: WebUI API initialization
- **READY**: Handler service ready
- **RUNNING**: Active request processing
- **STOPPING**: Graceful shutdown initiated
- **STOPPED**: Container terminated

### Service States
```
WebUI API: NOT_STARTED → INITIALIZING → LOADING_MODEL → READY → PROCESSING → SHUTDOWN
Handler:   NOT_STARTED → WAITING → READY → PROCESSING → SHUTDOWN
```

## Resource Lifecycle

### Memory Allocation Timeline
```
Time 0s:     Base container memory (~500MB)
Time 1s:     Environment setup (+50MB)
Time 5s:     Python dependencies (+1GB)
Time 30s:    Model loading (+4GB VRAM)
Time 60s:    Ready state (total ~5.5GB)
Runtime:     Dynamic allocation per request
```

### GPU Resource Timeline
```
Time 0s:     GPU detection ve driver loading
Time 30s:    CUDA context initialization
Time 45s:    Model loading to VRAM
Time 60s:    Ready for inference
Runtime:     Dynamic VRAM allocation
Shutdown:    CUDA context cleanup
```

## Error Scenarios ve Recovery

### Initialization Failures

#### 1. Model Loading Failure
- **Cause**: Corrupted model file, insufficient VRAM
- **Detection**: WebUI API startup errors
- **Recovery**: Container restart, model re-download

#### 2. GPU Access Failure
- **Cause**: Driver issues, GPU unavailable
- **Detection**: CUDA initialization errors
- **Recovery**: Host-level GPU troubleshooting

#### 3. Port Binding Failure
- **Cause**: Port already in use
- **Detection**: HTTP server startup error
- **Recovery**: Port configuration change

### Runtime Failures

#### 1. Service Crash
- **Cause**: Memory exhaustion, GPU errors
- **Detection**: Process monitoring
- **Recovery**: Service restart, resource cleanup

#### 2. Resource Exhaustion
- **Cause**: Memory leaks, GPU memory fragmentation
- **Detection**: Resource monitoring
- **Recovery**: Graceful restart, memory cleanup

## Monitoring ve Observability

### Lifecycle Monitoring Points
1. **Container Start**: Docker runtime logs
2. **Environment Setup**: start.sh script logs
3. **WebUI Launch**: Initialization progress logs
4. **Handler Ready**: Service readiness confirmation
5. **Request Processing**: Runtime operation logs
6. **Shutdown**: Cleanup process logs

### Health Indicators
- **Container Status**: Docker container state
- **Process Status**: Service process health
- **Resource Usage**: Memory ve GPU utilization
- **API Availability**: Endpoint responsiveness

### Performance Metrics
- **Startup Time**: Container ready duration
- **Memory Usage**: Peak ve average consumption
- **GPU Utilization**: Processing efficiency
- **Request Latency**: Response time tracking

## Optimization Strategies

### Startup Optimization
- **Model Caching**: Pre-loaded model persistence
- **Dependency Caching**: Python package caching
- **Parallel Initialization**: Concurrent service startup
- **Resource Pre-allocation**: Memory pool initialization

### Runtime Optimization
- **Connection Pooling**: HTTP session reuse
- **Memory Management**: Efficient allocation strategies
- **GPU Scheduling**: Optimal resource utilization
- **Request Batching**: Throughput improvement

### Shutdown Optimization
- **Graceful Termination**: Clean resource release
- **Fast Cleanup**: Efficient resource deallocation
- **State Persistence**: Critical data preservation
- **Quick Restart**: Minimal downtime recovery

Bu lifecycle workflow, container'ın tüm yaşam döngüsünü kapsar ve reliable operation için gerekli tüm süreçleri tanımlar.
