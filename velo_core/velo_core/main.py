import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from velo_core.config import get_settings
from velo_core.websocket.manager import manager
from velo_core.websocket.handlers import set_handler, handle_message
from velo_core.services.ollama import OllamaService
from velo_core.security import permission_gate
from velo_core.agent import Agent
from velo_core.audio import audio_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
agent = Agent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VELO 2.0 backend...")

    # Check Ollama
    ollama = OllamaService()
    if await ollama.health_check():
        logger.info("Ollama connection OK")
    else:
        logger.warning("Ollama not available - check if running")

    # Set up permission gate broadcast
    permission_gate.set_broadcast(manager.broadcast)

    # Start audio daemon
    audio_daemon.start()

    # Set up message handler
    set_handler(agent)

    yield

    logger.info("Shutting down VELO 2.0 backend...")
    audio_daemon.stop()


app = FastAPI(
    title="VELO 2.0 Backend",
    description="Local AI Assistant Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "velo_core"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            from velo_core.models.schemas import WSMessage
            message = WSMessage.model_validate_json(data)
            await handle_message(websocket, message)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "velo_core.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )