"""Application entrypoint for the InfiniteTalk FastAPI service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router


app = FastAPI(title="InfiniteTalk Service")

# 配置CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
