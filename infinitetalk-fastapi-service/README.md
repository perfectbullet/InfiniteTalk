# InfiniteTalk FastAPI 服务

该服务基于 `generate_infinitetalk.py` 命令封装了一个简洁的 FastAPI 接口，实现 FusioniX LoRA
推理流程、串行化任务执行，并提供日志查询能力。

## 项目结构

```
infinitetalk-fastapi-service/
├── app/
│   ├── api/
│   │   └── routes.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── command_executor.py
│   │   └── task_manager.py
│   └── main.py
├── logs/
│   └── execution.log
└── requirements.txt
```

## 安装依赖

```powershell
pip install -r requirements.txt
```

## 启动服务

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 接口说明

- `POST /generate`：提交视频生成任务，请求体参数为 `input_json` 与 `save_file`。
- `GET /logs`：读取执行日志的末尾片段。
- `GET /health`：基本健康检查。

服务一次仅允许一个生成任务并行执行；当已有任务运行时，新的请求会返回 HTTP 429。

## 备注

- API 在仓库根目录下执行，因此 `examples/single_example_zmh.json` 等相对路径可以直接使用。
- 命令的标准输出和标准错误会追加写入 `logs/execution.log`。
- 如需调整模型权重或命令参数，请修改 `app/services/command_executor.py`。