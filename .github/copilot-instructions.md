# InfiniteTalk AI Coding Agent Instructions

## 项目概览

InfiniteTalk 是基于 Wan2.1-I2V-14B 的视频生成项目，支持音频驱动的图像到视频（Image-to-Video）和视频到视频（Video-to-Video）生成，实现唇形同步与肢体动作协调。

**核心架构**：
- **生成引擎**：`generate_infinitetalk.py` - 命令行推理入口，调用 `wan/multitalk.py` 中的 `InfiniteTalkPipeline`
- **生产级 API**：`api_server/` - 完整的 FastAPI 服务（MongoDB + 异步任务队列 + 文件管理 + 绿幕去除）
- **模型层**：`wan/` 模块包含 DiT、VAE、T5、CLIP 等核心组件
- **音频处理**：`kokoro/` TTS 引擎 + `src/audio_analysis/` Wav2Vec2 特征提取

⚠️ **注意**：`infinitetalk-fastapi-service/` 是临时演示代码，不参与生产环境，忽略即可。

## 开发规范

- **语言**：所有文档和注释使用简体中文
- **环境管理**：虚拟环境统一命名为 `.venv`
- **日志规范**：所有服务输出日志到 `logs/` 目录
- **数据结构**：优先使用 Pydantic/dataclass 定义强类型，避免裸 dict

## 核心工作流

### 1. 视频生成命令（FusioniX LoRA 优化）

```bash
# 推荐配置（8 步快速推理）
python generate_infinitetalk.py \
    --ckpt_dir weights/Wan2.1-I2V-14B-480P \
    --wav2vec_dir weights/chinese-wav2vec2-base \
    --infinitetalk_dir weights/InfiniteTalk/single/infinitetalk.safetensors \
    --lora_dir Wan14BT2VFusioniX/FusionX_LoRa/Wan2.1_I2V_14B_FusionX_LoRA.safetensors \
    --input_json examples/single_example_image.json \
    --lora_scale 1.0 \
    --size infinitetalk-480 \
    --sample_steps 8 \
    --mode streaming \
    --motion_frame 9 \
    --sample_shift 2 \
    --save_file output.mp4
```

**参数说明**：
- `--size infinitetalk-480` → 640x640，`infinitetalk-720` → 960x960
- `--sample_steps 8`：FusioniX LoRA 优化后从 40 步降到 8 步
- `--motion_frame 9`：每 clip 生成的关键帧数（必须是 4n+1）
- `--mode streaming`：流式生成长视频

### 2. FastAPI 服务启动

```bash
# 启动生产级 API 服务（端口 50002）
uvicorn api_server.api_server:app --host 0.0.0.0 --port 50002

# 或使用启动脚本
python run_api_server.py
```

**核心特性**：
- MongoDB 存储任务/文件元数据
- 异步任务队列（`video_task_worker.py`）
- 文件上传/下载管理
- 绿幕去除服务集成（`routers/green_background_router.py`）
- 生命周期管理（启动时连接数据库，关闭时清理资源）

### 3. Docker 部署

```bash
docker-compose up -d
```

**关键配置**（`docker-compose.yml`）：
- `shm_size: 32gb` - 必须设置，避免多进程通信失败
- `CUDA_LAUNCH_BLOCKING=0` - 生产环境使用异步模式（调试时改为 1）
- GPU 分配：`count: all` + `capabilities: [gpu, compute, utility]`

## GPU 兼容性重要提示

### RTX 5090 (Blackwell SM 12.0) Flash Attention 问题

**症状**：`CUDA error: invalid argument` in `flash-attention/hopper/flash_fwd_launch_template.h`

**原因**：xformers 预编译版本针对 Hopper (SM 9.0)，不支持 Blackwell 架构

**解决方案**（按优先级）：

1. **临时禁用 Flash Attention**（生产环境可用）：
```python
# 在 generate_infinitetalk.py 开头添加
import torch
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(False)
torch.backends.cuda.enable_math_sdp(True)
```

2. **重新编译 xformers**（恢复性能）：
```bash
export TORCH_CUDA_ARCH_LIST="9.0;12.0"  # Hopper + Blackwell
pip uninstall xformers -y
pip install -v -U git+https://github.com/facebookresearch/xformers.git@main
```

**性能影响**：禁用后推理速度降低 30-50%，但稳定性最高

## 项目特定模式

### 1. 输入 JSON 格式

**单人模式**（`examples/single_example_image.json`）：
```json
{
  "ref_image": "examples/single/ref_image.png",
  "audio": "examples/single/1.wav"
}
```

**多人模式**（`examples/multi_example_image.json`）：包含 bbox 坐标定位多个人脸

### 2. 异步任务队列（api_server）

```python
# video_task_worker.py - 后台任务处理器
class VideoTaskWorker:
    async def start(self):
        # 持续轮询数据库中的待处理任务
        while self.running:
            tasks = await self._fetch_pending_tasks()
            for task in tasks:
                await self._process_task(task)

# 启动时自动创建后台任务
asyncio.create_task(video_task_worker.start())
```

### 3. LoRA 加载机制（wan/wan_lora.py）

```python
# 支持多个 LoRA 叠加
--lora_dir path1.safetensors path2.safetensors \
--lora_scale 1.0 0.8  # 对应每个 LoRA 的权重

# FusioniX LoRA 是官方推荐配置
# 位置：Wan14BT2VFusioniX/FusionX_LoRa/Wan2.1_I2V_14B_FusionX_LoRA.safetensors
```

## 调试技巧

### 1. 日志定位错误位置

```bash
# 设置同步模式，精确定位 CUDA 错误
export CUDA_LAUNCH_BLOCKING=1

# 查看完整堆栈（infinitetalk-fastapi-service）
tail -f infinitetalk-fastapi-service/logs/execution.log
```

### 2. 显存优化

```bash
# 环境变量配置（docker-compose.yml 或手动设置）
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,expandable_segments:True

# 降低参数减少显存占用
--sample_steps 4          # 从 8 降到 4
--motion_frame 5          # 从 9 降到 5
--num_persistent_param_in_dit 0  # 禁用持久化参数缓存
```

### 3. 检查模型加载

```python
# 在 generate_infinitetalk.py 中添加诊断
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
```

## 关键依赖版本

```
torch==2.4.1 (CUDA 12.1)
xformers==0.0.28
flash_attn==2.7.4.post1
diffusers>=0.31.0
transformers>=4.49.0
```

⚠️ **不要随意升级 PyTorch**，会导致 xformers/flash-attn 不兼容

## API 接口示例

```bash
# 上传图片
curl -X POST http://localhost:50002/api/upload/image \
  -F "file=@test.png"

# 创建任务
curl -X POST http://localhost:50002/api/video_tasks \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": "uuid-from-upload",
    "audio_id": "uuid-from-audio-upload",
    "task_type": "image_to_video"
  }'
```

## 常见陷阱

1. **相对路径问题**：`generate_infinitetalk.py` 需要在项目根目录执行，确保相对路径正确
2. **显存泄漏**：生成后调用 `torch.cuda.empty_cache()` + `gc.collect()`
3. **音频格式**：仅支持 16kHz 采样率的 WAV，自动重采样逻辑在 `generate_infinitetalk.py:custom_init`
4. **MongoDB 连接**：api_server 依赖 MongoDB，确保 docker-compose 中的 MongoDB 服务健康

## 下一步优化方向

- [ ] LCM distillation（进一步减少推理步数）
- [ ] TeaCache 加速（已支持，通过 `--use_teacache` 启用）
- [ ] int8 量化（通过 `--quant int8` 启用）
- [ ] Sparse Attention（长视频性能优化）

---

**更新日期**：2025-12-09  
**维护者**：根据 CLAUDE.md 规范定期审查并更新此文档
