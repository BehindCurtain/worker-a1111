# Alt Sistem: API Gateway

## Genel Bakış

API Gateway alt sistemi, RunPod serverless platform ile Automatic1111 WebUI API arasındaki köprü görevi görür. Request routing, error handling ve response formatting işlemlerinden sorumludur.

## Sorumluluklar

### 1. Request Processing
- **Input Validation**: RunPod event format kontrolü
- **Parameter Mapping**: RunPod input'u Automatic1111 API format'ına dönüştürme
- **Request Routing**: Local WebUI API endpoint'ine yönlendirme

### 2. Service Management
- **Health Checking**: WebUI API hazırlık durumu kontrolü
- **Connection Management**: HTTP session ve retry logic
- **Timeout Handling**: Request timeout yönetimi

### 3. Response Processing
- **Output Formatting**: API response'u RunPod format'ına dönüştürme
- **Error Handling**: Hata durumlarında graceful response
- **Logging**: Request/response tracking

## Teknik Detaylar

### Handler Architecture

#### RunPod Handler Pattern
```python
def handler(event):
    """RunPod serverless handler entry point"""
    json = run_inference(event["input"])
    return json
```

#### Core Components
- **Event Processing**: RunPod event structure parsing
- **Inference Execution**: Automatic1111 API call orchestration
- **Response Generation**: Standardized output formatting

### HTTP Client Configuration

#### Session Management
```python
automatic_session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
automatic_session.mount('http://', HTTPAdapter(max_retries=retries))
```

#### Retry Strategy
- **Total Retries**: 10 attempts
- **Backoff Factor**: 0.1 (exponential backoff)
- **Status Codes**: 502, 503, 504 (server errors)
- **Timeout**: 600 seconds per request

### Service Discovery

#### Health Check Mechanism
```python
def wait_for_service(url):
    """Service readiness polling"""
    # Continuous polling until service ready
    # Retry every 0.2 seconds
    # Log every 15 retries to avoid spam
```

#### Endpoint Configuration
- **Base URL**: http://127.0.0.1:3000/sdapi/v1
- **Health Check**: /sd-models endpoint
- **Inference**: /txt2img endpoint

## API Mapping

### Input Parameter Mapping

#### RunPod Event Structure
```json
{
  "input": {
    "prompt": "string",
    "negative_prompt": "string",
    "steps": "integer",
    "cfg_scale": "float",
    "width": "integer",
    "height": "integer",
    "sampler_name": "string"
  }
}
```

#### Automatic1111 API Parameters
- **Direct Mapping**: Tüm parametreler doğrudan geçirilir
- **Flexible Input**: Automatic1111 API'nin tüm parametrelerini destekler
- **Validation**: Implicit validation through API endpoint

### Response Processing

#### Output Structure
- **Direct Passthrough**: API response'u olduğu gibi döndürme
- **JSON Format**: Standardized JSON response
- **Error Propagation**: API hatalarını client'a iletme

## Error Handling Strategy

### Connection Errors
- **Network Issues**: Automatic retry with exponential backoff
- **Timeout Handling**: 600 second request timeout
- **Service Unavailable**: Continuous polling until ready

### API Errors
- **HTTP Status Codes**: Server error detection ve retry
- **Response Validation**: JSON format kontrolü
- **Error Propagation**: Client'a meaningful error messages

### 404 Error Recovery Mechanism
- **Multi-Attempt Strategy**: 3 attempts with 5-second delays
- **API Health Recovery**: Automatic service readiness re-check
- **Model Status Verification**: Post-recovery model availability check
- **txt2img Endpoint Recovery**: Specific endpoint availability verification

### Model Download Impact Handling
- **Download Detection**: Track when new models are downloaded
- **API Stability Check**: Verify WebUI API health after model downloads
- **Registry Update Wait**: 3-second delay for model registry updates
- **Graceful Degradation**: Continue with warnings if health checks fail

### Logging Strategy
- **Service Status**: Readiness check logging
- **Error Tracking**: Exception logging with context
- **Performance Metrics**: Request duration tracking
- **Recovery Operations**: Detailed recovery attempt logging

## Performance Optimizations

### Connection Pooling
- **Session Reuse**: HTTP connection pooling
- **Keep-Alive**: Persistent connections
- **Connection Limits**: Optimal connection management

### Request Optimization
- **Timeout Tuning**: 600 second timeout for complex generations
- **Retry Logic**: Smart retry with backoff
- **Resource Management**: Memory efficient request handling

### Caching Strategy
- **Session Caching**: HTTP session reuse
- **Connection Caching**: TCP connection pooling
- **No Response Caching**: Real-time generation requirement

## Security Considerations

### Network Security
- **Local Communication**: 127.0.0.1 binding (container internal)
- **No External Exposure**: WebUI API sadece container içinde erişilebilir
- **Request Validation**: Input sanitization through API layer

### Data Security
- **No Data Persistence**: Stateless request processing
- **Memory Management**: Request data lifecycle management
- **Error Information**: Sensitive data masking in errors

## Monitoring ve Observability

### Health Monitoring
- **Service Readiness**: Continuous health checking
- **Response Time**: Request duration tracking
- **Error Rate**: Failed request monitoring

### Logging Points
- **Service Startup**: WebUI API readiness logs
- **Request Processing**: Inference request logs
- **Error Conditions**: Exception ve retry logs

### Metrics Collection
- **Request Count**: Total inference requests
- **Response Time**: Average processing time
- **Error Rate**: Failed request percentage

## Integration Points

### RunPod Platform
- **Event Handling**: RunPod serverless event processing
- **Response Format**: Platform-compatible output
- **Error Reporting**: Platform error handling

### Automatic1111 WebUI
- **API Compatibility**: Full API parameter support
- **Version Compatibility**: v1.9.3 API specification
- **Feature Support**: txt2img endpoint focus

## Troubleshooting

### Common Issues
1. **Service Not Ready**: WebUI startup delays
2. **Connection Timeouts**: Network or processing delays
3. **Parameter Errors**: Invalid API parameters
4. **Memory Issues**: Large image generation requests

### Debug Strategies
- **Health Check Logs**: Service readiness tracking
- **Request Tracing**: Input/output logging
- **Error Analysis**: Exception stack trace analysis
- **Performance Profiling**: Request timing analysis

Bu alt sistem, projenin core functionality'sini sağlar ve tüm API trafiğinin güvenilir şekilde işlenmesini garanti eder.
