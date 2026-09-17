import logging
from fastapi import WebSocket, WebSocketDisconnect
from velo_core.websocket.manager import manager
from velo_core.models.schemas import (
    WSMessage,
    NotchStateMessage,
    TranscriptionMessage,
    PermissionRequestMessage,
    ToolCallMessage,
    ToolResultMessage,
    ErrorMessage,
    AudioChunkMessage,
    PermissionResponseMessage,
    WakeWordDetectedMessage,
    WSMessageType,
)
from velo_core.services.ollama import OllamaService
from velo_core.tools.base import TOOL_REGISTRY
from velo_core.security import PermissionGate

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, ollama: OllamaService, permission_gate: PermissionGate):
        self.ollama = ollama
        self.permission_gate = permission_gate
        self.audio_buffer: list[bytes] = []

    async def handle(self, websocket: WebSocket, message: WSMessage):
        try:
            if message.type == WSMessageType.AUDIO_CHUNK:
                await self._handle_audio_chunk(message)
            elif message.type == WSMessageType.WAKE_WORD_DETECTED:
                await self._handle_wake_word()
            elif message.type == WSMessageType.PERMISSION_RESPONSE:
                self.permission_gate.resolve(message.request_id, message.allowed)
            else:
                logger.warning(f"Unhandled message type: {message.type}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await manager.send_personal_message(
                ErrorMessage(message=f"Handler error: {str(e)}"), websocket
            )

    async def _handle_audio_chunk(self, message: AudioChunkMessage):
        # Accumulate audio for STT processing
        import base64
        audio_data = base64.b64decode(message.data)
        self.audio_buffer.append(audio_data)
        # Process when buffer reaches threshold (handled by STT daemon)

    async def _handle_wake_word(self):
        await manager.broadcast(NotchStateMessage(state="listening"))
        # Signal STT to start transcribing
        # This will be handled by the audio daemon

    async def process_user_input(self, text: str):
        """Process transcribed text through Ollama and execute tools."""
        await manager.broadcast(NotchStateMessage(state="expanded"))
        await manager.broadcast(TranscriptionMessage(text=text, final=True))

        # Get available tool schemas
        tools = [tool._tool_schema for tool in TOOL_REGISTRY.values()]

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": text},
        ]

        try:
            response = await self.ollama.chat(messages, tools)

            if response.message.tool_calls:
                for call in response.message.tool_calls:
                    await self._execute_tool_call(call)
            else:
                # Just a response, no tool calls
                await manager.broadcast(TranscriptionMessage(
                    text=response.message.content or "Done.", final=True
                ))
                await manager.broadcast(NotchStateMessage(state="idle"))

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            await manager.broadcast(ErrorMessage(message=str(e)))
            await manager.broadcast(NotchStateMessage(state="idle"))

    async def _execute_tool_call(self, call):
        tool_name = call.function.name
        args = call.function.arguments
        tool = TOOL_REGISTRY.get(tool_name)

        if not tool:
            await manager.broadcast(ToolResultMessage(
                request_id=call.id,
                success=False,
                error=f"Unknown tool: {tool_name}"
            ))
            return

        schema = tool._tool_schema

        # Check permission
        if schema.requires_permission:
            allowed = await self.permission_gate.request_permission(
                tool_name, args, schema.risk_level
            )
            if not allowed:
                await manager.broadcast(ToolResultMessage(
                    request_id=call.id,
                    success=False,
                    error="Permission denied by user"
                ))
                return

        await manager.broadcast(ToolCallMessage(
            id=call.id,
            tool=tool_name,
            args=args
        ))

        try:
            result = await tool(**args)
            await manager.broadcast(ToolResultMessage(
                request_id=call.id,
                success=True,
                output=str(result)
            ))
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            await manager.broadcast(ToolResultMessage(
                request_id=call.id,
                success=False,
                error=str(e)
            ))

    def _get_system_prompt(self) -> str:
        tool_descriptions = []
        for tool in TOOL_REGISTRY.values():
            schema = tool._tool_schema
            tool_descriptions.append(f"- {schema.name}: {schema.description}")
        tools_str = "\n".join(tool_descriptions)

        return f"""You are VELO, a local AI assistant. You can use tools to help the user.
Available tools:
{tools_str}

When the user asks you to do something, use the appropriate tool(s).
Be concise and helpful. Always confirm before taking actions that modify state."""


async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = WSMessage.model_validate_json(data)
            # Handler will be set up in main.py
            await handle_message(websocket, message)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


# Global handler instance (set in main.py)
_handler: MessageHandler | None = None


def set_handler(handler: MessageHandler):
    global _handler
    _handler = handler


async def handle_message(websocket: WebSocket, message: WSMessage):
    if _handler:
        await _handler.handle(websocket, message)