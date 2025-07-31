# Modül Haritası: Startup Script (start.sh)

## Genel Bakış

Startup script, container başlatma sürecini orchestrate eder. CUDA compatibility test, WebUI API ve RunPod handler servislerinin sıralı başlatılmasından, environment setup ve process management işlemlerinden sorumludur.

## Script Yapısı

### Shebang ve Environment
```bash
#!/usr/bin/env bash
```

### Execution Flow
1. **Initialization Logging**
2. **CUDA Compatibility Testing**
3. **Environment Setup**
4. **WebUI API Launch**
5. **Handler Service Start**
6. **Process Management**

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

### 2. CUDA Compatibility Test
```bash
echo "=============================================="
echo "RUNNING CUDA COMPATIBILITY TESTS"
echo "=============================================="

python /cuda_test.py
CUDA_TEST_EXIT_CODE=$?
```

#### Amaç
RTX 5090 CUDA compatibility'sini test eder ve sistem hazırlığını doğrular.

#### Teknik Detaylar
- **Test Script**: /cuda_test.py execution
- **Exit Code Capture**: $? ile test sonucu yakalama
- **RTX 5090 Support**: sm_120 compute capability kontrolü
- **PyTorch Verification**: CUDA 12.8 compatibility test

#### Test Sonuçları
```bash
if [ $CUDA_TEST_EXIT_CODE -eq 0 ]; then
    echo "🎉 CUDA compatibility test PASSED - RTX 5090 ready!"
elif [ $CUDA_TEST_EXIT_CODE -eq 1 ]; then
    echo "⚠ CUDA test passed with warnings - continuing with reduced performance"
else
    echo "❌ CUDA compatibility test FAILED"
    echo "❌ RTX 5090 may not be properly supported"
    echo "❌ Check the logs above for details"
    echo "⚠ Attempting to continue anyway..."
fi
```

#### Exit Code Meanings
- **0**: All tests passed, RTX 5090 fully supported
- **1**: CUDA works but xformers issues, reduced performance
- **2+**: CUDA compatibility issues, may not work properly

### 3. WebUI API Startup Announcement
```bash
echo "=============================================="
echo "STARTING WEBUI API"
echo "=============================================="
```

#### Amaç
WebUI API başlatma sürecinin başladığını belirtir.

#### Özellikler
- **Process Tracking**: Service startup logging
- **Debug Information**: Troubleshooting support
- **Sequential Logging**: Process order indication

### 4. Performance Optimization Setup
```bash
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
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

### 5. WebUI API Process Launch
```bash
python /stable-diffusion-webui/webui.py \
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
```

#### Amaç
Automatic1111 WebUI'yi API mode'da background process olarak başlatır.

#### Parameter Analizi

##### Performance Optimizations
- `--xformers`: Memory-efficient attention mechanism (CUDA 12.8 compatible)
- `--opt-sdp-attention`: Scaled dot-product attention optimization
- `--no-half-vae`: Full precision VAE for quality

##### Environment Compatibility
- `--skip-python-version-check`: Python version validation bypass
- `--skip-torch-cuda-test`: CUDA test bypass (already tested)
- `--skip-install`: Dependency installation bypass

##### Model Configuration
- `--ckpt-dir /runpod-volume/models/checkpoints`: Network volume checkpoint directory
- `--lora-dir /runpod-volume/models/loras`: Network volume LoRA directory
- `--embeddings-dir /runpod-volume/models/embeddings`: Network volume embeddings directory
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

### 6. Process Management
```bash
WEBUI_PID=$!
echo "WebUI API started with PID: $WEBUI_PID"
```

#### Amaç
Background process'in PID'ini yakalar ve monitoring için saklar.

#### Özellikler
- **PID Capture**: $! ile background process PID
- **Process Tracking**: PID logging for debugging
- **Process Management**: Shutdown coordination için PID saklama

### 7. Handler Service Startup
```bash
echo "=============================================="
echo "STARTING RUNPOD HANDLER"
echo "=============================================="

python -u /handler.py
```

#### Amaç
RunPod handler servisini foreground process olarak başlatır.

#### Özellikler
- **Foreground Execution**: Main process olarak çalışma
- **Unbuffered Output**: -u flag ile immediate output
- **Service Coordination**: WebUI API hazır olduktan sonra başlatma

### 8. Graceful Shutdown
```bash
echo "RunPod handler exited, stopping WebUI API..."
kill $WEBUI_PID 2>/dev/null || true
wait $WEBUI_PID 2>/dev/null || true
echo "Shutdown complete."
```

#### Amaç
Handler service exit olduğunda WebUI API'yi de temiz şekilde kapatır.

#### Özellikler
- **Process Termination**: SIGTERM signal gönderme
- **Error Suppression**: 2>/dev/null ile error hiding
- **Process Waiting**: wait ile process completion
- **Graceful Shutdown**: Clean termination sequence

## Process Management Strategy

### Service Orchestration
```
1. CUDA Compatibility Test
2. Environment Setup (tcmalloc, Python)
3. WebUI API Launch (Background)
4. Handler Service Start (Foreground)
5. Graceful Shutdown (Both services)
```

### Process Hierarchy
- **Parent Process**: start.sh script
- **Background Child**: WebUI API process
- **Foreground Child**: Handler service process

### Process Communication
- **Implicit Coordination**: Handler service WebUI API'yi bekler
- **Port-based Communication**: 3000 port üzerinden HTTP
- **Process Isolation**: Separate process spaces
- **PID Management**: Background process tracking

## CUDA Compatibility Integration

### Test Sequence
1. **PyTorch Version Check**: 2.7.0+ verification
2. **CUDA Availability**: torch.cuda.is_available()
3. **GPU Detection**: Device count and properties
4. **Compute Capability**: sm_120 support verification
5. **Tensor Operations**: GPU functionality test
6. **Xformers Test**: Optimization library compatibility

### Error Handling
- **Test Failure**: Continue with warnings
- **Partial Success**: Reduced performance mode
- **Complete Success**: Full RTX 5090 optimization

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
- **CUDA Test Integration**: Compatibility verification
- **Graceful Shutdown**: Clean process termination

### Failure Scenarios
1. **CUDA Test Failure**: Continue with warnings
2. **tcmalloc Not Found**: Script continues without optimization
3. **WebUI Launch Failure**: Background process failure
4. **Handler Failure**: Foreground process termination

### Recovery Mechanisms
- **Container Restart**: Platform-level recovery
- **Process Monitoring**: External health checks
- **Graceful Degradation**: Service-level fallbacks

## Performance Characteristics

### Startup Sequence
1. **Immediate**: Environment setup (< 1 second)
2. **Fast**: CUDA compatibility test (5-10 seconds)
3. **Medium**: WebUI API initialization (30-60 seconds)
4. **Fast**: Handler service start (< 5 seconds)

### Resource Usage
- **Memory**: tcmalloc optimization active
- **GPU**: CUDA 12.8 with RTX 5090 support
- **CPU**: Parallel service initialization
- **I/O**: Unbuffered Python output

### Optimization Features
- **Memory Allocator**: tcmalloc performance boost
- **CUDA Compatibility**: RTX 5090 sm_120 support
- **Attention Mechanism**: xformers optimization
- **Model Loading**: Pre-loaded model strategy

## Integration Points

### Container Integration
- **Entry Point**: Docker CMD execution
- **Environment Variables**: Container-level configuration
- **Process Management**: Container lifecycle management

### Service Integration
- **CUDA Test**: Compatibility verification
- **WebUI API**: Background service initialization
- **Handler Service**: Foreground service execution
- **Port Management**: Service communication setup

## Monitoring ve Logging

### Startup Logging
- **Process Initiation**: "Worker Initiated"
- **CUDA Testing**: Compatibility test results
- **Service Startup**: "Starting WebUI API"
- **Handler Launch**: "Starting RunPod Handler"
- **Shutdown**: "Shutdown complete"

### Process Visibility
- **CUDA Test**: Detailed compatibility information
- **Background Process**: WebUI API PID logging
- **Foreground Process**: Handler service visible output
- **Environment Logging**: tcmalloc detection implicit

## Troubleshooting

### Common Issues
1. **CUDA Compatibility Failure**: RTX 5090 not supported
2. **tcmalloc Not Found**: Performance degradation
3. **Port Conflicts**: Service binding failures
4. **Model Loading Errors**: WebUI initialization failures
5. **Handler Connection Errors**: Service communication issues

### Debug Strategies
- **CUDA Test Analysis**: /cuda_test.py detailed output
- **Process Monitoring**: ps aux | grep python
- **Port Checking**: netstat -tlnp | grep 3000
- **Log Analysis**: Container log examination
- **Environment Verification**: env | grep -E "(LD_PRELOAD|PYTHON)"

### RTX 5090 Specific Debugging
- **Compute Capability**: nvidia-smi --query-gpu=compute_cap --format=csv
- **PyTorch Version**: python -c "import torch; print(torch.__version__)"
- **CUDA Version**: python -c "import torch; print(torch.version.cuda)"
- **GPU Detection**: python -c "import torch; print(torch.cuda.device_count())"

### Performance Tuning
- **Memory Allocation**: tcmalloc configuration
- **CUDA Optimization**: RTX 5090 specific tuning
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

Bu script, projenin tüm servislerinin coordinated ve optimized şekilde başlatılmasını sağlar, RTX 5090 compatibility'sini doğrular ve system reliability'yi garanti eder.
