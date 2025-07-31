import os
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

# Network volume paths
MODELS_BASE_PATH = "/workspace/models"
CHECKPOINTS_PATH = f"{MODELS_BASE_PATH}/checkpoints"
LORAS_PATH = f"{MODELS_BASE_PATH}/loras"
EMBEDDINGS_PATH = f"{MODELS_BASE_PATH}/embeddings"
CACHE_REGISTRY_PATH = f"{MODELS_BASE_PATH}/cache_registry.json"

class ModelManager:
    def __init__(self):
        self.ensure_directories()
        self.cache_registry = self.load_cache_registry()
        
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for path in [CHECKPOINTS_PATH, LORAS_PATH, EMBEDDINGS_PATH]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def load_cache_registry(self) -> Dict:
        """Load model cache registry from JSON file"""
        if os.path.exists(CACHE_REGISTRY_PATH):
            try:
                with open(CACHE_REGISTRY_PATH, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load cache registry, creating new one")
        
        return {
            "checkpoints": {},
            "loras": {},
            "embeddings": {},
            "last_updated": time.time()
        }
    
    def save_cache_registry(self):
        """Save cache registry to JSON file"""
        self.cache_registry["last_updated"] = time.time()
        try:
            with open(CACHE_REGISTRY_PATH, 'w') as f:
                json.dump(self.cache_registry, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache registry: {e}")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except IOError:
            return ""
    
    def verify_model_integrity(self, file_path: str, expected_hash: Optional[str] = None) -> bool:
        """Verify model file integrity"""
        if not os.path.exists(file_path):
            return False
        
        if expected_hash:
            actual_hash = self.calculate_file_hash(file_path)
            return actual_hash == expected_hash
        
        # If no hash provided, just check if file exists and is not empty
        return os.path.getsize(file_path) > 0
    
    def download_model(self, url: str, destination: str, expected_hash: Optional[str] = None) -> bool:
        """Download model from URL to destination"""
        try:
            print(f"Downloading model from {url} to {destination}")
            
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Download with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded_size % (100 * 1024 * 1024) == 0:
                            progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                            print(f"Download progress: {progress:.1f}%")
            
            # Verify integrity if hash provided
            if expected_hash and not self.verify_model_integrity(destination, expected_hash):
                print(f"Hash verification failed for {destination}")
                os.remove(destination)
                return False
            
            print(f"Successfully downloaded model to {destination}")
            return True
            
        except Exception as e:
            print(f"Error downloading model from {url}: {e}")
            if os.path.exists(destination):
                os.remove(destination)
            return False
    
    def get_or_download_checkpoint(self, name: str, url: str, expected_hash: Optional[str] = None) -> Optional[str]:
        """Get checkpoint from cache or download if not available"""
        cache_path = os.path.join(CHECKPOINTS_PATH, f"{name}.safetensors")
        
        # Check if model exists in cache and is valid
        if name in self.cache_registry["checkpoints"]:
            cached_info = self.cache_registry["checkpoints"][name]
            if self.verify_model_integrity(cache_path, expected_hash):
                print(f"Using cached checkpoint: {name}")
                cached_info["last_used"] = time.time()
                cached_info["usage_count"] = cached_info.get("usage_count", 0) + 1
                self.save_cache_registry()
                return cache_path
        
        # Download model if not in cache or invalid
        if self.download_model(url, cache_path, expected_hash):
            # Update cache registry
            self.cache_registry["checkpoints"][name] = {
                "url": url,
                "path": cache_path,
                "hash": expected_hash or self.calculate_file_hash(cache_path),
                "downloaded_at": time.time(),
                "last_used": time.time(),
                "usage_count": 1,
                "file_size": os.path.getsize(cache_path)
            }
            self.save_cache_registry()
            return cache_path
        
        return None
    
    def get_or_download_lora(self, name: str, url: str, expected_hash: Optional[str] = None) -> Optional[str]:
        """Get LoRA from cache or download if not available"""
        cache_path = os.path.join(LORAS_PATH, f"{name}.safetensors")
        
        # Check if LoRA exists in cache and is valid
        if name in self.cache_registry["loras"]:
            cached_info = self.cache_registry["loras"][name]
            if self.verify_model_integrity(cache_path, expected_hash):
                print(f"Using cached LoRA: {name}")
                cached_info["last_used"] = time.time()
                cached_info["usage_count"] = cached_info.get("usage_count", 0) + 1
                self.save_cache_registry()
                return cache_path
        
        # Download LoRA if not in cache or invalid
        if self.download_model(url, cache_path, expected_hash):
            # Update cache registry
            self.cache_registry["loras"][name] = {
                "url": url,
                "path": cache_path,
                "hash": expected_hash or self.calculate_file_hash(cache_path),
                "downloaded_at": time.time(),
                "last_used": time.time(),
                "usage_count": 1,
                "file_size": os.path.getsize(cache_path)
            }
            self.save_cache_registry()
            return cache_path
        
        return None
    
    def prepare_models_for_request(self, checkpoint_info: Optional[Dict] = None, loras: Optional[List[Dict]] = None) -> Tuple[Optional[str], List[Tuple[str, float]]]:
        """Prepare models for inference request"""
        checkpoint_path = None
        lora_paths = []
        
        # Handle checkpoint
        if checkpoint_info:
            checkpoint_path = self.get_or_download_checkpoint(
                checkpoint_info["name"],
                checkpoint_info["url"],
                checkpoint_info.get("hash")
            )
            if not checkpoint_path:
                print(f"Failed to prepare checkpoint: {checkpoint_info['name']}")
        
        # Handle LoRAs
        if loras:
            for lora_info in loras:
                lora_path = self.get_or_download_lora(
                    lora_info["name"],
                    lora_info["url"],
                    lora_info.get("hash")
                )
                if lora_path:
                    scale = lora_info.get("scale", 1.0)
                    lora_paths.append((lora_path, scale))
                else:
                    print(f"Failed to prepare LoRA: {lora_info['name']}")
        
        return checkpoint_path, lora_paths
    
    def build_lora_prompt(self, base_prompt: str, lora_paths: List[Tuple[str, float]]) -> str:
        """Build prompt with LoRA syntax"""
        if not lora_paths:
            return base_prompt
        
        lora_tags = []
        for lora_path, scale in lora_paths:
            lora_name = os.path.splitext(os.path.basename(lora_path))[0]
            lora_tags.append(f"<lora:{lora_name}:{scale}>")
        
        # Add LoRA tags to the beginning of the prompt
        lora_string = " ".join(lora_tags)
        return f"{lora_string} {base_prompt}".strip()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            "checkpoints": {
                "count": len(self.cache_registry["checkpoints"]),
                "total_size": 0
            },
            "loras": {
                "count": len(self.cache_registry["loras"]),
                "total_size": 0
            },
            "disk_usage": {}
        }
        
        # Calculate sizes
        for checkpoint_info in self.cache_registry["checkpoints"].values():
            stats["checkpoints"]["total_size"] += checkpoint_info.get("file_size", 0)
        
        for lora_info in self.cache_registry["loras"].values():
            stats["loras"]["total_size"] += lora_info.get("file_size", 0)
        
        # Get disk usage
        try:
            import shutil
            total, used, free = shutil.disk_usage(MODELS_BASE_PATH)
            stats["disk_usage"] = {
                "total": total,
                "used": used,
                "free": free
            }
        except:
            pass
        
        return stats
    
    def cleanup_old_models(self, max_age_days: int = 30, keep_popular: int = 10):
        """Clean up old, unused models to free space"""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        # Get models sorted by usage
        all_models = []
        
        for name, info in self.cache_registry["checkpoints"].items():
            all_models.append(("checkpoint", name, info))
        
        for name, info in self.cache_registry["loras"].items():
            all_models.append(("lora", name, info))
        
        # Sort by usage count (descending) and last used (descending)
        all_models.sort(key=lambda x: (x[2].get("usage_count", 0), x[2].get("last_used", 0)), reverse=True)
        
        # Keep popular models and remove old ones
        models_to_remove = []
        for i, (model_type, name, info) in enumerate(all_models):
            if i >= keep_popular:  # Beyond popular threshold
                last_used = info.get("last_used", 0)
                if current_time - last_used > max_age_seconds:
                    models_to_remove.append((model_type, name, info))
        
        # Remove old models
        for model_type, name, info in models_to_remove:
            try:
                if os.path.exists(info["path"]):
                    os.remove(info["path"])
                    print(f"Removed old {model_type}: {name}")
                
                if model_type == "checkpoint":
                    del self.cache_registry["checkpoints"][name]
                else:
                    del self.cache_registry["loras"][name]
                    
            except Exception as e:
                print(f"Error removing {model_type} {name}: {e}")
        
        if models_to_remove:
            self.save_cache_registry()
            print(f"Cleaned up {len(models_to_remove)} old models")

# Global model manager instance
model_manager = ModelManager()
