import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, TypeAdapter

from velo_core.config import get_settings
from velo_core.websocket.manager import manager
from velo_core.websocket.handlers import set_handler, handle_message, MessageHandler
from velo_core.services.ollama import OllamaService
from velo_core.security import permission_gate
from velo_core.audio import audio_daemon

# Import all tool modules so TOOL_REGISTRY is populated on startup
import velo_core.tools.browser      # noqa: F401
import velo_core.tools.shell        # noqa: F401
import velo_core.tools.search       # noqa: F401
import velo_core.tools.antigravity  # noqa: F401
import velo_core.tools.gmail        # noqa: F401
import velo_core.tools.teams        # noqa: F401

from velo_core.models.schemas import WSMessage, UserInputMessage, NotchStateMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Type adapter for discriminated union deserialization
ws_message_adapter = TypeAdapter(WSMessage)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VELO 2.0 backend...")

    # Instantiate services (must be inside lifespan so event loop is running)
    ollama = OllamaService()
    if await ollama.health_check():
        logger.info("✅ Ollama connection OK")
    else:
        logger.warning("⚠️  Ollama not available — start with: ollama serve")

    # Wire permission gate to WebSocket broadcast
    permission_gate.set_broadcast(manager.broadcast)

    # Create and register the message handler
    handler = MessageHandler(ollama, permission_gate)
    set_handler(handler)

    # Start audio daemon (wake-word + STT)
    audio_daemon.start()

    from velo_core.tools.base import TOOL_REGISTRY
    logger.info(f"✅ Tool registry: {list(TOOL_REGISTRY.keys())}")

    yield

    logger.info("Shutting down VELO 2.0 backend...")
    audio_daemon.stop()


app = FastAPI(
    title="VELO 2.0 Backend",
    description="Local AI Assistant Orchestrator",
    version="0.2.0",
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
    from velo_core.tools.base import TOOL_REGISTRY
    return {
        "status": "ok",
        "service": "velo_core",
        "tools": list(TOOL_REGISTRY.keys()),
    }


class TextInputRequest(BaseModel):
    text: str


@app.post("/input")
async def text_input(body: TextInputRequest):
    """HTTP endpoint for text-mode testing without wake word / microphone."""
    from velo_core.websocket.handlers import _handler
    if not _handler:
        raise HTTPException(status_code=503, detail="Handler not ready")
    await manager.broadcast(NotchStateMessage(state="listening"))
    await _handler.process_user_input(body.text)
    return {"status": "processing", "text": body.text}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = ws_message_adapter.validate_json(data)
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
        reload=False,  # reload=True breaks background threads
        log_level=settings.log_level.lower(),
    )