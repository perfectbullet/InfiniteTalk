# 绿色背景去除服务

这是一个基于 FastAPI 的视频绿色背景去除服务，可以将绿幕视频转换为透明背景视频。

## 功能特性

1. **视频转换接口** (`POST /convert`)
   - 去除视频中的绿色背景
   - 转换为指定格式（如 MOV、WebM）
   - 自动跳过已转换的文件
   - 后台异步处理，不阻塞请求

2. **日志查看接口** (`GET /logs/{filename}`)
   - 查看转换任务的日志文件
   - 实时监控转换进度和错误信息

3. **健康检查接口** (`GET /health`)
   - 检查服务运行状态

## 安装依赖

### 系统依赖

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Python 依赖

```bash
# 使用 uv（推荐）
uv pip install -r green_bg_removal_service/requirements.txt

# 或使用 pip
pip install -r green_bg_removal_service/requirements.txt
```

## 使用方法

### 启动服务

```bash
# 使用提供的启动脚本
./scripts/start_green_bg_service.sh

# 或手动启动
uvicorn green_bg_removal_service.app:app --host 0.0.0.0 --port 8000
```

### API 调用示例

#### 1. 转换视频

```bash
curl -X POST "http://localhost:8000/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "/path/to/input.mp4",
    "output_format": "mov"
  }'
```

响应示例：

```json
{
  "status": "started",
  "message": "转换任务已启动，进程 PID: 12345",
  "output_path": "output_videos/input.mov",
  "log_path": "logs/input.log"
}
```

#### 2. 查看日志

```bash
curl "http://localhost:8000/logs/input.log"
```

#### 3. 健康检查

```bash
curl "http://localhost:8000/health"
```

响应：

```json
{
  "status": "ok"
}
```

## 目录结构

```
.
├── green_bg_removal_service/
│   ├── __init__.py
│   ├── app.py              # FastAPI 应用主文件
│   └── requirements.txt    # Python 依赖
├── scripts/
│   ├── start_green_bg_service.sh  # 启动脚本
│   └── test_green_bg_service.py   # 测试脚本
├── output_videos/          # 输出视频目录
└── logs/                   # 日志文件目录
```

## 配置参数

转换命令使用以下默认参数：

- `--similarity 0.35`: 绿色相似度阈值
- `--blend 0.1`: 边缘混合程度
- `--despill-mix 0.9`: 色溢去除强度
- `--despill-expand 0.1`: 色溢扩展范围

这些参数已经过优化，适用于大多数绿幕视频。

## 注意事项

1. **输出格式**：建议使用 `.mov` 或 `.webm` 格式以支持透明通道
2. **文件路径**：输入文件必须存在，输出文件会自动保存到 `output_videos/` 目录
3. **日志文件**：所有日志统一保存到 `logs/` 目录
4. **格式验证**：输出格式不能与输入格式相同
5. **后台处理**：转换任务在后台异步执行，通过日志文件查看进度

## 测试

运行测试脚本：

```bash
# 启动服务后在另一个终端运行
python3 scripts/test_green_bg_service.py
```

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
