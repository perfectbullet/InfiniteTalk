# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 任何项目都务必遵守的规则（极其重要！！！）

## Communication

- 永远使用简体中文进行思考和对话

## Documentation

- 编写 .md 文档时，也要用中文
- 正式文档写到项目的 docs/ 目录下
- 用于讨论和评审的计划、方案等文档，写到项目的 discuss/ 目录下

## Code Architecture

- 编写代码的硬性指标，包括以下原则：
 （1）对于 Python、JavaScript、TypeScript 等动态语言，尽可能确保每个代码文件不要超过 300 行
 （2）对于 Java、Go、Rust 等静态语言，尽可能确保每个代码文件不要超过 400 行
 （3）每层文件夹中的文件，尽可能不超过 8 个。如有超过，需要规划为多层子文件夹
- 除了硬性指标以外，还需要时刻关注优雅的架构设计，避免出现以下可能侵蚀我们代码质量的「坏味道」：
 （1）僵化 (Rigidity): 系统难以变更，任何微小的改动都会引发一连串的连锁修改。
 （2）冗余 (Redundancy): 同样的代码逻辑在多处重复出现，导致维护困难且容易产生不一致。
 （3）循环依赖 (Circular Dependency): 两个或多个模块互相纠缠，形成无法解耦的"死结"，导致难以测试与复用。
 （4）脆弱性 (Fragility): 对代码一处的修改，导致了系统中其他看似无关部分功能的意外损坏。
 （5）晦涩性 (Obscurity): 代码意图不明，结构混乱，导致阅读者难以理解其功能和设计。
 （6）数据泥团 (Data Clump): 多个数据项总是一起出现在不同方法的参数中，暗示着它们应该被组合成一个独立的对象。
 （7）不必要的复杂性 (Needless Complexity): 用"杀牛刀"去解决"杀鸡"的问题，过度设计使系统变得臃肿且难以理解。
- 【非常重要！！】无论是你自己编写代码，还是阅读或审核他人代码时，都要严格遵守上述硬性指标，以及时刻关注优雅的架构设计。
- 【非常重要！！】无论何时，一旦你识别出那些可能侵蚀我们代码质量的「坏味道」，都应当立即询问用户是否需要优化，并给出合理的优化建议。

## Run & Debug

- 对于所有 Run & Debug 操作，优先使用项目中已有的启动脚本（如 `run_api_server.py`）
- 如果脚本执行失败，无论是脚本本身的问题还是其他代码问题，需要先紧急修复
- Run & Debug 之前，为所有项目配置 Logger with File Output，并统一输出到 logs/ 目录下

## Python

- 数据结构尽可能全部定义成强类型。如果个别场景不得不使用未经结构化定义的 dict，需要先停下来征求用户的同意
- Python 虚拟环境永远使用 .venv 作为目录名
- 项目的根目录必须保持简洁，只保留必须存在的文件
- main.py 内容也要简洁。只保留必须存在的代码

---

# InfiniteTalk 项目架构指南

## 项目概览

InfiniteTalk 是基于 Wan2.1-I2V-14B 的音频驱动视频生成模型，支持以下功能：

- **单人/多人动画**：基于音频生成口型同步视频
- **FusioniX LoRA 优化**：从 40 步降到 8 步快速推理
- **流式生成**：支持无限长度视频生成
- **TeaCache 加速**：通过缓存减少重复计算
- **量化支持**：int8/fp8 量化降低显存占用

## 核心架构

### 1. 推理引擎（命令行）

**入口文件**：`generate_infinitetalk.py`

- 解析命令行参数和 JSON 输入配置
- 加载 `wan.InfiniteTalkPipeline`（定义在 `wan/multitalk.py`）
- 使用 Wav2Vec2 提取音频特征
- 调用 Kokoro TTS 生成语音（可选）
- 使用 FFmpeg 合成最终视频

### 2. 生产级 API 服务

**目录结构**：`api_server/`

- **api_server.py**：FastAPI 应用主文件，包含所有路由
- **config.py**：环境变量和配置管理
- **database.py**：MongoDB 数据库操作（Motor 异步驱动）
- **models.py**：Pydantic 数据模型（ImageInfo、TaskInfo、AudioInfo 等）
- **video_task_worker.py**：异步任务队列处理器
- **InfiniteTalkGenerator.py**：封装 `generate_infinitetalk.py` 的生成逻辑
- **routers/**：路由模块（task_logs、video_task、green_background_router）
- **utils.py**：工具函数（文件上传、绿幕服务调用等）

**启动脚本**：`run_api_server.py`

### 3. 模型层

**目录**：`wan/`

- **multitalk.py**：`InfiniteTalkPipeline` 核心生成类
- **modules/**：DiT、VAE、T5、CLIP、Attention 等模型组件
- **configs/**：不同分辨率和任务类型的配置（infinitetalk-480/720）
- **wan_lora.py**：LoRA 加载和融合逻辑
- **utils/**：采样器、视频处理、多模态处理工具

### 4. 音频处理

- **kokoro/**：Kokoro TTS 引擎（文本转语音）
- **src/audio_analysis/wav2vec2.py**：Wav2Vec2 音频特征提取

## 常用命令

### 视频生成（FusioniX LoRA 优化）

```bash
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

**关键参数**：
- `--size infinitetalk-480`：640x640 分辨率；`infinitetalk-720`：960x960
- `--sample_steps 8`：FusioniX LoRA 优化后的步数
- `--motion_frame 9`：每 clip 生成的关键帧数（必须是 4n+1）
- `--mode streaming`：流式生成长视频
- `--num_persistent_param_in_dit 0`：降低显存占用

### 启动 API 服务

```bash
# 方式1：直接运行
python run_api_server.py

# 方式2：使用 uvicorn
uvicorn api_server.api_server:app --host 0.0.0.0 --port 50002

# 方式3：Docker 部署
docker-compose up -d
```

### Docker 部署

```bash
docker-compose up -d
```

**关键配置**（`docker-compose.yml`）：
- `shm_size: 32gb`：必须设置，避免多进程通信失败
- `CUDA_LAUNCH_BLOCKING=0`：生产环境使用异步模式（调试时改为 1）
- GPU 分配：`count: all` + `capabilities: [gpu, compute, utility]`

### 多 GPU 推理

```bash
GPU_NUM=8
torchrun --nproc_per_node=$GPU_NUM --standalone generate_infinitetalk.py \
    --ckpt_dir weights/Wan2.1-I2V-14B-480P \
    --wav2vec_dir weights/chinese-wav2vec2-base \
    --infinitetalk_dir weights/InfiniteTalk/single/infinitetalk.safetensors \
    --dit_fsdp --t5_fsdp \
    --ulysses_size=$GPU_NUM \
    --input_json examples/single_example_image.json \
    --size infinitetalk-480 \
    --sample_steps 40 \
    --mode streaming \
    --motion_frame 9 \
    --save_file output.mp4
```

## GPU 兼容性

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

## 输入格式

### 单人模式 JSON（`examples/single_example_image.json`）

```json
{
  "ref_image": "path/to/image.png",
  "audio": "path/to/audio.wav"
}
```

### 多人模式 JSON（`examples/multi_example_image.json`）

```json
{
  "ref_image": "path/to/image.png",
  "audio": "path/to/audio.wav",
  "bbox": [[x1, y1, x2, y2], ...]  // 多个人脸的边界框
}
```

## 显存优化

```bash
# 环境变量配置
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,expandable_segments:True

# 参数调优
--sample_steps 4          # 从 8 降到 4
--motion_frame 5          # 从 9 降到 5
--num_persistent_param_in_dit 0  # 禁用持久化参数缓存
--use_teacache            # 启用 TeaCache 加速
--quant int8              # 启用 int8 量化
```

## 关键依赖版本

```
torch==2.4.1 (CUDA 12.1)
xformers==0.0.28
flash_attn==2.7.4.post1
diffusers>=0.31.0
transformers>=4.49.0
motor>=3.6.0  # MongoDB 异步驱动
```

⚠️ **不要随意升级 PyTorch**，会导致 xformers/flash-attn 不兼容

## API 接口示例

```bash
# 上传图片
curl -X POST http://localhost:50002/api/images/upload \
  -F "person_name=测试人物" \
  -F "file=@test.png"

# 创建任务
curl -X POST http://localhost:50002/api/tasks/create \
  -F "prompt=一位小朋友在热情的说话" \
  -F "image_path=/path/to/image.jpg" \
  -F "audio_path=/path/to/audio.wav" \
  -F "use_green_background=true"

# 查询任务状态
curl http://localhost:50002/api/tasks/{task_id}

# 获取任务列表
curl http://localhost:50002/api/tasks?status=completed&limit=20

# 下载生成的视频
curl http://localhost:50002/api/download/video/{filename} -o output.mp4
```

## 调试技巧

### 1. 同步模式定位 CUDA 错误

```bash
export CUDA_LAUNCH_BLOCKING=1
```

### 2. 查看日志

```bash
# API 服务日志
tail -f logs/info.log

# 生成日志
tail -f logs/execution.log
```

### 3. 检查模型加载

```python
# 在 generate_infinitetalk.py 中添加诊断
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"Compute Capability: {torch.cuda.get_device_capability(0)}")
```

## 常见陷阱

1. **相对路径问题**：`generate_infinitetalk.py` 需要在项目根目录执行
2. **显存泄漏**：生成后调用 `torch.cuda.empty_cache()` + `gc.collect()`
3. **音频格式**：仅支持 16kHz 采样率的 WAV，自动重采样逻辑在 `generate_infinitetalk.py:audio_prepare_single`
4. **MongoDB 连接**：api_server 依赖 MongoDB，确保 docker-compose 中的 MongoDB 服务健康
5. **绿幕服务超时**：绿幕服务默认等待 120 秒，超时后降级使用原图
