"""Application entrypoint for the InfiniteTalk FastAPI service."""

from fastapi import FastAPI

from .api.routes import router


app = FastAPI(title="InfiniteTalk Service")
app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
# infinite_talk_service/
# │
# ├── app.py
# ├── generate_infinitetalk.py  # Copy the original script here
# ├── requirements.txt
# └── logs/
#     └── execution.log