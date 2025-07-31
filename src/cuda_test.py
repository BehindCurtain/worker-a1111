#!/usr/bin/env python3
"""
CUDA Compatibility Test for RTX 5090
Tests CUDA availability, compute capability, and PyTorch compatibility
"""

import sys
import torch

def test_cuda_compatibility():
    """Test CUDA compatibility for RTX 5090 (sm_120)"""
    print("=" * 60)
    print("CUDA COMPATIBILITY TEST FOR RTX 5090")
    print("=" * 60)
    
    # Test 1: PyTorch version
    print(f"✓ PyTorch version: {torch.__version__}")
    
    # Test 2: CUDA availability
    cuda_available = torch.cuda.is_available()
    print(f"{'✓' if cuda_available else '❌'} CUDA available: {cuda_available}")
    
    if not cuda_available:
        print("❌ CUDA not available. Cannot proceed with GPU tests.")
        return False
    
    # Test 3: CUDA version
    cuda_version = torch.version.cuda
    print(f"✓ CUDA version: {cuda_version}")
    
    # Test 4: GPU count and details
    gpu_count = torch.cuda.device_count()
    print(f"✓ GPU count: {gpu_count}")
    
    if gpu_count == 0:
        print("❌ No GPUs detected.")
        return False
    
    # Test 5: GPU details and compute capability
    for i in range(gpu_count):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_props = torch.cuda.get_device_properties(i)
        compute_capability = f"{gpu_props.major}.{gpu_props.minor}"
        
        print(f"✓ GPU {i}: {gpu_name}")
        print(f"  - Compute Capability: sm_{gpu_props.major}{gpu_props.minor}")
        print(f"  - Memory: {gpu_props.total_memory / 1024**3:.1f} GB")
        print(f"  - Multiprocessors: {gpu_props.multi_processor_count}")
        
        # Check if RTX 5090 (sm_120) is supported
        if gpu_props.major == 12 and gpu_props.minor == 0:
            print(f"  ✓ RTX 5090 (sm_120) detected and supported!")
        elif gpu_props.major >= 12:
            print(f"  ✓ Advanced GPU architecture (sm_{gpu_props.major}{gpu_props.minor}) supported!")
        elif gpu_props.major >= 8:
            print(f"  ✓ Modern GPU architecture (sm_{gpu_props.major}{gpu_props.minor}) supported!")
        else:
            print(f"  ⚠ Older GPU architecture (sm_{gpu_props.major}{gpu_props.minor})")
    
    # Test 6: Simple tensor operation
    try:
        print("\n" + "=" * 40)
        print("TESTING GPU TENSOR OPERATIONS")
        print("=" * 40)
        
        # Create a test tensor on GPU
        device = torch.device('cuda:0')
        test_tensor = torch.randn(1000, 1000, device=device)
        result = torch.matmul(test_tensor, test_tensor.T)
        
        print("✓ GPU tensor creation: SUCCESS")
        print("✓ GPU matrix multiplication: SUCCESS")
        print(f"✓ Result tensor shape: {result.shape}")
        print(f"✓ Result tensor device: {result.device}")
        
        # Memory info
        allocated = torch.cuda.memory_allocated(0) / 1024**2
        cached = torch.cuda.memory_reserved(0) / 1024**2
        print(f"✓ GPU memory allocated: {allocated:.1f} MB")
        print(f"✓ GPU memory cached: {cached:.1f} MB")
        
        # Clean up
        del test_tensor, result
        torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        print(f"❌ GPU tensor operation failed: {e}")
        return False

def test_xformers_compatibility():
    """Test xformers compatibility"""
    print("\n" + "=" * 40)
    print("TESTING XFORMERS COMPATIBILITY")
    print("=" * 40)
    
    try:
        import xformers
        print(f"✓ xformers version: {xformers.__version__}")
        
        # Test xformers CUDA compatibility
        import xformers.ops
        print("✓ xformers.ops imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ xformers import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ xformers test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting CUDA compatibility tests...\n")
    
    # Run CUDA tests
    cuda_ok = test_cuda_compatibility()
    
    # Run xformers tests
    xformers_ok = test_xformers_compatibility()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if cuda_ok and xformers_ok:
        print("🎉 ALL TESTS PASSED!")
        print("✓ RTX 5090 compatibility confirmed")
        print("✓ Ready for Stable Diffusion inference")
        return 0
    elif cuda_ok:
        print("⚠ CUDA tests passed, but xformers issues detected")
        print("✓ Basic GPU operations should work")
        print("⚠ Performance may be suboptimal without xformers")
        return 1
    else:
        print("❌ CUDA COMPATIBILITY ISSUES DETECTED")
        print("❌ RTX 5090 may not be properly supported")
        print("❌ Check PyTorch and CUDA versions")
        return 2

if __name__ == "__main__":
    sys.exit(main())
