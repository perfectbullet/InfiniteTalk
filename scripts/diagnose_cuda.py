import torch
import os

print("=== 环境诊断 ===")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"CUDA Version: {torch.version.cuda}")
print(f"cuDNN Version: {torch.backends.cudnn.version()}")

if torch.cuda.is_available():
    print(f"\nGPU: {torch.cuda.get_device_name(0)}")
    print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
    
    # 测试基本 CUDA 操作
    try:
        x = torch.randn(100, 100).cuda()
        y = torch.randn(100, 100).cuda()
        z = torch.matmul(x, y)
        print("\n✓ 基本 CUDA 运算正常")
    except Exception as e:
        print(f"\n✗ CUDA 运算失败: {e}")
    
    # 测试注意力机制
    try:
        from torch.nn import MultiheadAttention
        attn = MultiheadAttention(embed_dim=512, num_heads=8).cuda()
        q = torch.randn(10, 2, 512).cuda()
        output, _ = attn(q, q, q)
        print("✓ 标准注意力机制正常")
    except Exception as e:
        print(f"✗ 注意力机制失败: {e}")

# 检查环境变量
print(f"\n=== 相关环境变量 ===")
for key in ['WAN_DISABLE_FLASH_ATTENTION', 'XFORMERS_FORCE_DISABLE_TRITON', 
            'CUDA_VISIBLE_DEVICES', 'PYTORCH_CUDA_ALLOC_CONF']:
    print(f"{key}: {os.environ.get(key, 'Not Set')}")