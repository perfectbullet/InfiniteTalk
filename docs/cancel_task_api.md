# 视频任务取消功能

## 功能说明

新增了取消正在运行的视频生成任务的功能，支持通过 API 接口杀死对应的进程，真正终止任务执行。

## API 接口

### 1. 取消任务

**接口**: `POST /video_task/cancel/{task_id}`

**参数**:
- `task_id` (路径参数): 要取消的任务ID

**返回示例**:

成功取消:
```json
{
  "success": true,
  "message": "任务 video_20231219_120000_abcd1234 已成功取消",
  "task_id": "video_20231219_120000_abcd1234",
  "previous_status": "running",
  "current_status": "cancelled"
}
```

任务已完成，无法取消:
```json
{
  "success": false,
  "message": "任务已经处于 success 状态，无法取消",
  "task_id": "video_20231219_120000_abcd1234",
  "current_status": "success"
}
```

**错误响应**:
- `404`: 任务不存在
- `500`: 取消失败（进程无法终止等）

### 2. 查询任务状态

**接口**: `GET /video_task/status/{task_id}`

**参数**:
- `task_id` (路径参数): 任务ID

**返回示例**:
```json
{
  "id": "video_20231219_120000_abcd1234",
  "status": "running",
  "prompt": "视频生成提示词",
  "image_path": "/path/to/image.png",
  "audio_path": "/path/to/audio.wav",
  "pid": 12345,
  "uptime": 45.5,
  "created_at": "2023-12-19T12:00:00",
  "started_at": "2023-12-19T12:00:05",
  "log_path": "/workspace/InfiniteTalk/logs/task_video_20231219_120000_abcd1234.log"
}
```

## 工作原理

1. **接收取消请求**: API 接收 `/video_task/cancel/{task_id}` 请求
2. **验证任务状态**: 检查任务是否存在及当前状态
3. **调用 Worker**: 调用 `VideoTaskWorker.cancel_task()` 方法
4. **杀死进程**: 通过 `InfiniteTalkGenerator.cancel()` 发送终止信号
   - 首先尝试优雅终止 (`SIGTERM`)
   - 5 秒后未响应则强制终止 (`SIGKILL`)
5. **更新数据库**: 将任务状态更新为 `cancelled`
6. **清理资源**: 关闭日志文件，移除进程记录

## 使用示例

### cURL 命令

```bash
# 取消任务
curl -X POST http://localhost:50002/video_task/cancel/video_20231219_120000_abcd1234

# 查询任务状态
curl http://localhost:50002/video_task/status/video_20231219_120000_abcd1234
```

### Python 客户端

```python
import requests

API_BASE = "http://localhost:50002"

# 取消任务
task_id = "video_20231219_120000_abcd1234"
response = requests.post(f"{API_BASE}/video_task/cancel/{task_id}")
result = response.json()

if result['success']:
    print(f"✅ 任务已取消: {task_id}")
else:
    print(f"❌ 取消失败: {result['message']}")

# 查询状态
response = requests.get(f"{API_BASE}/video_task/status/{task_id}")
task_info = response.json()
print(f"任务状态: {task_info['status']}")
```

### 测试脚本

使用提供的测试脚本快速测试功能：

```bash
# 完整测试流程（创建 -> 等待 -> 取消）
python scripts/test_cancel_task.py

# 直接取消指定任务
python scripts/test_cancel_task.py cancel video_20231219_120000_abcd1234

# 查询任务状态
python scripts/test_cancel_task.py status video_20231219_120000_abcd1234
```

## 任务状态说明

- `pending`: 等待执行
- `processing`: 正在准备（生成配置文件等）
- `running`: 进程运行中
- `success`: 成功完成
- `failed`: 执行失败
- `cancelled`: 已被取消 ⭐

只有 `pending`、`processing`、`running` 状态的任务可以被取消。

## 注意事项

1. **进程终止**: 取消操作会立即杀死对应的 Python 进程，可能导致临时文件未清理
2. **资源清理**: 已生成的部分视频文件不会被自动删除，需要手动清理
3. **日志保留**: 任务日志文件会被保留，方便后续分析
4. **重复取消**: 多次取消同一任务是安全的，已取消的任务会返回相应提示
5. **并发安全**: 取消操作是异步安全的，不会影响其他正在运行的任务

## 故障排查

### 取消失败

如果取消任务失败，可能的原因：

1. **进程不存在**: 任务已自行完成或崩溃
   - 解决方案: 检查任务日志和状态

2. **权限不足**: 无法向进程发送信号
   - 解决方案: 检查运行 API 服务的用户权限

3. **僵尸进程**: 进程未正常响应终止信号
   - 解决方案: 手动使用 `kill -9 <PID>` 强制终止

### 查看进程状态

```bash
# 查看所有 Python 视频生成进程
ps aux | grep generate_infinitetalk.py

# 手动终止进程
kill -9 <PID>
```

## 扩展功能建议

- [ ] 批量取消任务
- [ ] 取消时自动清理临时文件
- [ ] 支持暂停/恢复任务
- [ ] WebSocket 实时推送任务状态变化
