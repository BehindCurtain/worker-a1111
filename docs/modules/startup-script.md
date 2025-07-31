# Modül Haritası: Startup Script (start.sh)

## Genel Bakış

Startup script, container başlatma sürecini orchestrate eder. WebUI API ve RunPod handler servislerinin sıralı başlatılmasından, environment setup ve process management işlemlerinden sorumludur.

## Script Yapısı

### Shebang ve Environment
```bash
#!/usr/bin/env bash
```

### Execution Flow
1. **Initialization Logging**
2. **Environment Setup**
3. **WebUI API Launch**
4. **Handler Service Start**

## Komut Analizi

### 1. Worker Initialization
```bash
echo "Worker Initiated"
```

#### Amaç
Container başlatma sürecinin başladığını loglar.

#### Özellikler
- **Startup Logging**: Process başlangıç indicator
- **Debug Support**: Container lifecycle tracking
- **Simple Output**: Minimal logging overhead

### 2. WebUI API Startup Announcement
```bash
echo "Starting WebUI API"
```

#### Amaç
WebUI API başlatma sürecinin başladığını belirtir.

#### Özellikler
- **Process Tracking**: Service startup logging
- **Debug Information**: Troubleshooting support
- **Sequential Logging**: Process order indication

### 3. Performance Optimization Setup
```bash
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
```

#### Amaç
tcmalloc memory allocator'ı sistem genelinde aktif eder.

#### Teknik Detaylar
- **Library Detection**: Dynamic library path discovery
- **Pattern Matching**: Regex-based library identification
- **Environment Export**: LD_PRELOAD global setting
- **Memory Optimization**: Improved allocation performance

#### İşleyiş
1. **ldconfig Query**: Installed library listing
2. **Regex Filtering**: tcmalloc library pattern matching
3. **First Match**: head -n 1 ile ilk match selection
4. **Environment Setting**: LD_PRELOAD variable export

### 4. Python Environment Configuration
```bash
export PYTHONUNBUFFERED=true
```

#### Amaç
Python output buffering'i deaktive eder.

#### Özellikler
- **Real-time Logging**: Immediate output visibility
- **Debug Support**: Live process monitoring
- **Container Compatibility**: Docker logging optimization

### 5. WebUI API Process Launch
```bash
python /stable-diffusion-webui/webui.py \
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

#### Amaç
Automatic1111 WebUI'yi API mode'da background process olarak başlatır.

#### Parameter Analizi

##### Performance Optimizations
- `--xformers`: Memory-efficient attention mechanism
- `--opt-sdp-attention`: Scaled dot-product attention optimization
- `--no-half-vae`: Full precision VAE for quality

##### Environment Compatibility
- `--skip-python-version-check`: Python version validation bypass
- `--skip-torch-cuda-test`: CUDA test bypass
- `--skip-install`: Dependency installation bypass

##### Model Configuration
- `--ckpt /model.safetensors`: Pre-loaded model path
- `--no-download-sd-model`: Model download bypass
- `--no-hashing`: Model hash calculation bypass

##### API Configuration
- `--port 3000`: API server port
- `--api`: API mode activation
- `--nowebui`: Web interface deactivation

##### Security ve Performance
- `--disable-safe-unpickle`: Performance over security
- `--skip-version-check`: Version validation bypass

##### Background Execution
- `&`: Background process execution

### 6. Handler Service Startup
```bash
echo "Starting RunPod Handler"
python -u /handler.py
```

#### Amaç
RunPod handler servisini foreground process olarak başlatır.

#### Özellikler
- **Foreground Execution**: Main process olarak çalışma
- **Unbuffered Output**: -u flag ile immediate output
- **Service Coordination**: WebUI API hazır olduktan sonra başlatma

## Process Management Strategy

### Service Orchestration
```
1. Environment Setup (tcmalloc, Python)
2. WebUI API Launch (Background)
3. Handler Service Start (Foreground)
```

### Process Hierarchy
- **Parent Process**: start.sh script
- **Background Child**: WebUI API process
- **Foreground Child**: Handler service process

### Process Communication
- **Implicit Coordination**: Handler service WebUI API'yi bekler
- **Port-based Communication**: 3000 port üzerinden HTTP
- **Process Isolation**: Separate process spaces

## Environment Management

### Memory Optimization
```bash
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
```

### Python Configuration
```bash
export PYTHONUNBUFFERED=true
```

### Global Environment
- **LD_PRELOAD**: Memory allocator override
- **PYTHONUNBUFFERED**: Output buffering control

## Error Handling

### Script Robustness
- **Library Detection**: tcmalloc availability check
- **Process Isolation**: Background/foreground separation
- **Implicit Error Handling**: Process-level error management

### Failure Scenarios
1. **tcmalloc Not Found**: Script continues without optimization
2. **WebUI Launch Failure**: Background process failure
3. **Handler Failure**: Foreground process termination

### Recovery Mechanisms
- **Container Restart**: Platform-level recovery
- **Process Monitoring**: External health checks
- **Graceful Degradation**: Service-level fallbacks

## Performance Characteristics

### Startup Sequence
1. **Immediate**: Environment setup (< 1 second)
2. **Medium**: WebUI API initialization (30-60 seconds)
3. **Fast**: Handler service start (< 5 seconds)

### Resource Usage
- **Memory**: tcmalloc optimization active
- **CPU**: Parallel service initialization
- **I/O**: Unbuffered Python output

### Optimization Features
- **Memory Allocator**: tcmalloc performance boost
- **Attention Mechanism**: xformers optimization
- **Model Loading**: Pre-loaded model strategy

## Integration Points

### Container Integration
- **Entry Point**: Docker CMD execution
- **Environment Variables**: Container-level configuration
- **Process Management**: Container lifecycle management

### Service Integration
- **WebUI API**: Background service initialization
- **Handler Service**: Foreground service execution
- **Port Management**: Service communication setup

## Monitoring ve Logging

### Startup Logging
- **Process Initiation**: "Worker Initiated"
- **Service Startup**: "Starting WebUI API"
- **Handler Launch**: "Starting RunPod Handler"

### Process Visibility
- **Background Process**: WebUI API silent startup
- **Foreground Process**: Handler service visible output
- **Environment Logging**: tcmalloc detection implicit

## Troubleshooting

### Common Issues
1. **tcmalloc Not Found**: Performance degradation
2. **Port Conflicts**: Service binding failures
3. **Model Loading Errors**: WebUI initialization failures
4. **Handler Connection Errors**: Service communication issues

### Debug Strategies
- **Process Monitoring**: ps aux | grep python
- **Port Checking**: netstat -tlnp | grep 3000
- **Log Analysis**: Container log examination
- **Environment Verification**: env | grep -E "(LD_PRELOAD|PYTHON)"

### Performance Tuning
- **Memory Allocation**: tcmalloc configuration
- **WebUI Parameters**: Optimization flag tuning
- **Process Priorities**: CPU scheduling optimization
- **Resource Limits**: Container resource management

## Security Considerations

### Process Security
- **Background Execution**: WebUI API isolation
- **Port Binding**: Local interface binding (127.0.0.1)
- **File Permissions**: Script execution permissions

### Configuration Security
- **Safe Unpickle Disabled**: Performance vs security trade-off
- **Model Path**: Trusted model source
- **API Access**: Container-internal access only

Bu script, projenin tüm servislerinin coordinated ve optimized şekilde başlatılmasını sağlar ve system reliability'yi garanti eder.
