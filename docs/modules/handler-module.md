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

### 1. wait_for_service(url)

#### Amaç
WebUI API servisinin hazır olmasını bekler ve service readiness kontrolü yapar.

#### Parametreler
- `url` (string): Kontrol edilecek service endpoint URL'i

#### İşleyiş
```python
def wait_for_service(url):
    retries = 0
    while True:
        try:
            requests.get(url, timeout=120)
            return
        except requests.exceptions.RequestException:
            retries += 1
            if retries % 15 == 0:
                print("Service not ready yet. Retrying...")
        except Exception as err:
            print("Error: ", err)
        time.sleep(0.2)
```

#### Özellikler
- **Infinite Loop**: Servis hazır olana kadar sürekli kontrol
- **Timeout**: 120 saniye request timeout
- **Logging**: Her 15 retry'da bir log mesajı
- **Sleep Interval**: 0.2 saniye bekleme süresi
- **Error Handling**: Generic exception handling

#### Kullanım Senaryoları
- Container startup sırasında WebUI API hazırlık kontrolü
- Service health check operations
- Dependency service validation

### 2. run_inference(inference_request)

#### Amaç
Automatic1111 WebUI API'sine inference request gönderir ve response alır.

#### Parametreler
- `inference_request` (dict): txt2img API için request parametreleri

#### İşleyiş
```python
def run_inference(inference_request):
    response = automatic_session.post(url=f'{LOCAL_URL}/txt2img',
                                      json=inference_request, timeout=600)
    return response.json()
```

#### Özellikler
- **Session Reuse**: Global session object kullanımı
- **JSON Request**: Automatic JSON serialization
- **Long Timeout**: 600 saniye timeout (image generation için)
- **Direct Response**: JSON response'u doğrudan döndürme
- **Error Propagation**: HTTP errors otomatik propagation

#### Request Flow
1. **Input Validation**: Implicit through API endpoint
2. **HTTP POST**: Session-based request execution
3. **Response Processing**: JSON deserialization
4. **Output Return**: Direct response passthrough

### 3. handler(event)

#### Amaç
RunPod serverless platform için ana entry point fonksiyonu.

#### Parametreler
- `event` (dict): RunPod event object containing input data

#### İşleyiş
```python
def handler(event):
    json = run_inference(event["input"])
    return json
```

#### Özellikler
- **Event Processing**: RunPod event structure parsing
- **Input Extraction**: event["input"] field extraction
- **Inference Delegation**: run_inference fonksiyonuna delegation
- **Direct Return**: Response'u olduğu gibi döndürme

#### Integration Points
- **RunPod Platform**: Serverless event handling
- **Inference Engine**: WebUI API integration
- **Error Handling**: Implicit through underlying functions

## Modül İlişkileri

### Internal Dependencies
- **wait_for_service**: Service readiness validation
- **run_inference**: Core inference processing
- **handler**: Platform integration layer

### External Dependencies
- **runpod**: Serverless platform SDK
- **requests**: HTTP client library
- **time**: Sleep ve timing operations

### Data Flow
```
RunPod Event → handler() → run_inference() → WebUI API
                ↓
RunPod Response ← JSON Response ← HTTP Response
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
