# Modül Haritası: Model Manager (model_manager.py)

## Genel Bakış

Model Manager modülü, RunPod Network Volume üzerinde checkpoint ve LoRA modellerinin yönetiminden sorumludur. Model download, cache, integrity verification ve lifecycle management işlevlerini sağlar.

## Modül Yapısı

### Import Dependencies
```python
import os
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
```

### Global Configuration
```python
MODELS_BASE_PATH = "/workspace/models"
CHECKPOINTS_PATH = f"{MODELS_BASE_PATH}/checkpoints"
LORAS_PATH = f"{MODELS_BASE_PATH}/loras"
EMBEDDINGS_PATH = f"{MODELS_BASE_PATH}/embeddings"
CACHE_REGISTRY_PATH = f"{MODELS_BASE_PATH}/cache_registry.json"
```

## Sınıf Analizi: ModelManager

### 1. __init__(self)

#### Amaç
ModelManager instance'ını initialize eder ve gerekli dizinleri oluşturur.

#### İşleyiş
```python
def __init__(self):
    self.ensure_directories()
    self.cache_registry = self.load_cache_registry()
```

#### Özellikler
- **Directory Creation**: Network volume dizinlerini oluşturma
- **Cache Loading**: Mevcut cache registry'yi yükleme
- **Initialization**: Model manager state setup

### 2. ensure_directories(self)

#### Amaç
Network volume üzerinde gerekli dizin yapısını oluşturur.

#### İşleyiş
- **Checkpoints Directory**: `/workspace/models/checkpoints`
- **LoRAs Directory**: `/workspace/models/loras`
- **Embeddings Directory**: `/workspace/models/embeddings`
- **Recursive Creation**: `parents=True, exist_ok=True`

#### Error Handling
- **Permission Errors**: Directory creation failure handling
- **Path Validation**: Directory accessibility check

### 3. load_cache_registry(self) -> Dict

#### Amaç
Model cache registry'sini JSON dosyasından yükler.

#### Registry Structure
```json
{
  "checkpoints": {
    "model_name": {
      "url": "download_url",
      "path": "local_path",
      "hash": "sha256_hash",
      "downloaded_at": timestamp,
      "last_used": timestamp,
      "usage_count": integer,
      "file_size": bytes
    }
  },
  "loras": { /* same structure */ },
  "embeddings": { /* same structure */ },
  "last_updated": timestamp
}
```

#### Error Recovery
- **Corrupted JSON**: Fallback to empty registry
- **Missing File**: Create new registry
- **IO Errors**: Graceful degradation

### 4. calculate_file_hash(self, file_path: str) -> str

#### Amaç
Dosyanın SHA256 hash'ini hesaplar.

#### İşleyiş
```python
def calculate_file_hash(self, file_path: str) -> str:
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()
```

#### Özellikler
- **Chunk Processing**: Memory-efficient large file handling
- **SHA256 Algorithm**: Cryptographic hash function
- **Error Handling**: File access error management

### 5. verify_model_integrity(self, file_path: str, expected_hash: Optional[str]) -> bool

#### Amaç
Model dosyasının integrity'sini doğrular.

#### Validation Levels
1. **File Existence**: Dosyanın var olup olmadığı
2. **File Size**: Dosyanın boş olmaması
3. **Hash Verification**: Expected hash ile karşılaştırma

#### Use Cases
- **Download Verification**: İndirilen dosyanın doğruluğu
- **Cache Validation**: Cache'deki dosyanın bozulmamış olması
- **Integrity Check**: Periodic integrity validation

### 6. download_model(self, url: str, destination: str, expected_hash: Optional[str]) -> bool

#### Amaç
Model dosyasını URL'den indirir ve doğrular.

#### Download Process
1. **HTTP Request**: Streaming download with timeout
2. **Progress Tracking**: 100MB intervals ile progress logging
3. **File Writing**: Chunk-based file writing
4. **Integrity Verification**: Hash validation if provided
5. **Cleanup**: Failed download cleanup

#### Performance Features
- **Streaming Download**: Memory-efficient large file handling
- **Progress Logging**: Download progress visibility
- **Timeout Handling**: 300 second timeout
- **Resume Support**: Potential for resume functionality

#### Error Scenarios
- **Network Errors**: Connection failures, timeouts
- **Disk Space**: Insufficient storage space
- **Hash Mismatch**: Corrupted download detection
- **Permission Errors**: File write permission issues

### 7. get_or_download_checkpoint(self, name: str, url: str, expected_hash: Optional[str]) -> Optional[str]

#### Amaç
Checkpoint'i cache'den alır veya indirir.

#### Cache Logic
1. **Cache Hit**: Model cache'de mevcut ve valid
2. **Cache Miss**: Model cache'de yok veya invalid
3. **Download**: Cache miss durumunda download
4. **Registry Update**: Successful download sonrası cache update

#### Usage Tracking
- **Last Used**: Access timestamp update
- **Usage Count**: Access frequency tracking
- **Statistics**: Cache hit/miss metrics

### 8. get_or_download_lora(self, name: str, url: str, expected_hash: Optional[str]) -> Optional[str]

#### Amaç
LoRA modelini cache'den alır veya indirir.

#### İşleyiş
- **Identical Logic**: Checkpoint ile aynı cache logic
- **LoRA Specific**: LoRA registry section kullanımı
- **File Extension**: `.safetensors` extension handling

### 9. prepare_models_for_request(self, checkpoint_info: Optional[Dict], loras: Optional[List[Dict]]) -> Tuple[Optional[str], List[Tuple[str, float]]]

#### Amaç
Request için gerekli modelleri hazırlar.

#### Input Processing
```python
# Checkpoint info
{
  "name": "model_name",
  "url": "download_url",
  "hash": "optional_hash"
}

# LoRA info
[
  {
    "name": "lora_name",
    "url": "download_url", 
    "scale": 0.8,
    "hash": "optional_hash"
  }
]
```

#### Output Format
```python
(checkpoint_path, [(lora_path, scale), ...])
```

#### Error Handling
- **Download Failures**: Individual model failure handling
- **Partial Success**: Continue with available models
- **Logging**: Failed model preparation logging

### 10. build_lora_prompt(self, base_prompt: str, lora_paths: List[Tuple[str, float]]) -> str

#### Amaç
LoRA syntax'ını prompt'a entegre eder.

#### LoRA Syntax
```
<lora:model_name:scale>
```

#### Prompt Building
```python
# Input
base_prompt = "beautiful landscape"
lora_paths = [("/path/to/landscape.safetensors", 0.8)]

# Output
"<lora:landscape:0.8> beautiful landscape"
```

#### Features
- **Multiple LoRAs**: Multiple LoRA support
- **Scale Integration**: Custom scale values
- **Name Extraction**: Filename-based LoRA naming

### 11. get_cache_stats(self) -> Dict

#### Amaç
Cache istatistiklerini döndürür.

#### Statistics
```python
{
  "checkpoints": {
    "count": 5,
    "total_size": 20480000000  # bytes
  },
  "loras": {
    "count": 15,
    "total_size": 2048000000   # bytes
  },
  "disk_usage": {
    "total": 107374182400,     # bytes
    "used": 53687091200,       # bytes
    "free": 53687091200        # bytes
  }
}
```

#### Use Cases
- **Monitoring**: Cache usage monitoring
- **Cleanup Decisions**: Storage management
- **Performance Metrics**: Cache efficiency tracking

### 12. cleanup_old_models(self, max_age_days: int = 30, keep_popular: int = 10)

#### Amaç
Eski ve kullanılmayan modelleri temizler.

#### Cleanup Strategy
1. **Usage Sorting**: Usage count ve last used sorting
2. **Popular Retention**: En popüler N modeli koru
3. **Age Filtering**: Belirli yaştan eski modelleri sil
4. **Registry Update**: Cache registry güncelleme

#### Parameters
- **max_age_days**: Maximum model age threshold
- **keep_popular**: Number of popular models to retain

#### Benefits
- **Storage Management**: Disk space optimization
- **Performance**: Cache efficiency improvement
- **Cost Reduction**: Storage cost optimization

## Global Instance

### model_manager
```python
# Global model manager instance
model_manager = ModelManager()
```

#### Singleton Pattern
- **Global Access**: Tüm modüllerden erişilebilir
- **State Persistence**: Cache state korunması
- **Resource Sharing**: Shared model cache

## Integration Points

### Handler Integration
```python
from model_manager import model_manager

# Request processing
checkpoint_path, lora_paths = model_manager.prepare_models_for_request(
    checkpoint_info, loras
)
```

### WebUI Integration
- **Directory Configuration**: WebUI model directories
- **Model Discovery**: Automatic model detection
- **Runtime Loading**: Dynamic model switching

## Performance Characteristics

### Download Performance
- **Streaming**: Memory-efficient downloads
- **Progress Tracking**: Real-time progress updates
- **Parallel Downloads**: Potential concurrent downloads
- **Resume Support**: Interrupted download recovery

### Cache Performance
- **Fast Lookup**: O(1) cache lookup
- **Metadata Caching**: Registry-based metadata
- **Integrity Checking**: Hash-based verification
- **Usage Tracking**: Access pattern analysis

### Storage Efficiency
- **Deduplication**: Same model multiple references
- **Compression**: Safetensors format efficiency
- **Cleanup**: Automatic old model removal
- **Monitoring**: Storage usage tracking

## Error Handling

### Network Errors
- **Timeout Handling**: Download timeout management
- **Retry Logic**: Failed download retry
- **Fallback Strategies**: Alternative download sources
- **Error Propagation**: Meaningful error messages

### Storage Errors
- **Disk Full**: Storage exhaustion handling
- **Permission Errors**: File access permission issues
- **Corruption Detection**: Hash mismatch handling
- **Recovery Mechanisms**: Corrupted file cleanup

### Cache Errors
- **Registry Corruption**: JSON parsing errors
- **Metadata Inconsistency**: Cache-file mismatch
- **Concurrent Access**: Multi-process safety
- **Recovery Strategies**: Cache rebuild mechanisms

## Monitoring ve Observability

### Logging Points
- **Download Progress**: Model download tracking
- **Cache Operations**: Hit/miss logging
- **Error Conditions**: Failure scenario logging
- **Performance Metrics**: Operation timing

### Metrics Collection
- **Cache Hit Rate**: Cache efficiency metrics
- **Download Statistics**: Download success/failure rates
- **Storage Usage**: Disk space utilization
- **Model Popularity**: Usage frequency tracking

Bu modül, projenin model management foundation'ını oluşturur ve efficient, reliable model caching sistemini sağlar.
