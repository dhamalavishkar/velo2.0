import logging
from pydantic import TypeAdapter
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
    ActivationMessage,
    UserInputMessage,
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
        self._conversation: list[dict] = []  # Multi-turn history

    async def handle(self, websocket: WebSocket, message):
        """Dispatch incoming WebSocket message to the correct handler."""
        try:
            msg_type = message.type

            if msg_type == WSMessageType.AUDIO_CHUNK:
                await self._handle_audio_chunk(message)
            elif msg_type == WSMessageType.WAKE_WORD_DETECTED:
                await self._handle_wake_word()
            elif msg_type == WSMessageType.PERMISSION_RESPONSE:
                self.permission_gate.resolve(message.request_id, message.allowed)
            elif msg_type == WSMessageType.USER_INPUT:
                await self.process_user_input(message.text)
            else:
                logger.debug(f"Unhandled client message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await manager.send_personal_message(
                ErrorMessage(message=f"Handler error: {str(e)}"), websocket
            )

    async def _handle_audio_chunk(self, message: AudioChunkMessage):
        import base64
        from velo_core.audio import audio_daemon
        audio_data = base64.b64decode(message.data)
        audio_daemon.stt.add_audio(audio_data) if hasattr(audio_daemon.stt, "add_audio") else None

    async def _handle_wake_word(self):
        await manager.broadcast(NotchStateMessage(state="activation"))
        import asyncio
        await asyncio.sleep(1.5)
        await manager.broadcast(NotchStateMessage(state="listening"))

    async def process_user_input(self, text: str):
        """Process transcribed / typed text through Ollama and execute tools."""
        logger.info(f"Processing user input: {text!r}")
        await manager.broadcast(NotchStateMessage(state="expanded"))
        await manager.broadcast(TranscriptionMessage(text=text, final=True))

        # Build tool list from registry
        tools = [tool._tool_schema for tool in TOOL_REGISTRY.values()]

        # Maintain conversation history for multi-turn context
        if not self._conversation:
            self._conversation.append({
                "role": "system",
                "content": self._system_prompt(),
            })
        self._conversation.append({"role": "user", "content": text})

        try:
            response = await self.ollama.chat(self._conversation, tools)
            reply = response.message

            if reply.tool_calls:
                # Execute all requested tool calls
                for call in reply.tool_calls:
                    result_text = await self._execute_tool_call(call)
                    # Add assistant + tool result to history
                    self._conversation.append({"role": "assistant", "content": None, "tool_calls": [
                        {"id": call.id, "function": {"name": call.function.name, "arguments": call.function.arguments}}
                    ]})
                    self._conversation.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result_text,
                    })
                # Get follow-up response from Ollama after tool execution
                follow_up = await self.ollama.chat(self._conversation, tools)
                if follow_up.message.content:
                    await manager.broadcast(TranscriptionMessage(
                        text=follow_up.message.content, final=True
                    ))
                    self._conversation.append({
                        "role": "assistant",
                        "content": follow_up.message.content,
                    })
            else:
                content = reply.content or "Done."
                await manager.broadcast(TranscriptionMessage(text=content, final=True))
                self._conversation.append({"role": "assistant", "content": content})

        except Exception as e:
            logger.error(f"Ollama error: {e}", exc_info=True)
            await manager.broadcast(ErrorMessage(message=str(e)))

        finally:
            await manager.broadcast(NotchStateMessage(state="idle"))

        # Trim history to last 20 turns to avoid token overflow
        if len(self._conversation) > 22:
            self._conversation = self._conversation[:1] + self._conversation[-20:]

    async def _execute_tool_call(self, call) -> str:
        """Execute a tool call, respecting HITL permission gate. Returns result text."""
        tool_name = call.function.name
        args = call.function.arguments or {}
        tool = TOOL_REGISTRY.get(tool_name)

        if not tool:
            err = f"Unknown tool: {tool_name}"
            await manager.broadcast(ToolResultMessage(request_id=call.id, success=False, error=err))
            return err

        schema = tool._tool_schema

        # --- HITL permission check ---
        if schema.requires_permission:
            await manager.broadcast(NotchStateMessage(state="permission"))
            allowed = await self.permission_gate.request_permission(
                tool_name, args, schema.risk_level
            )
            if not allowed:
                denied_msg = "Permission denied by user"
                await manager.broadcast(ToolResultMessage(
                    request_id=call.id, success=False, error=denied_msg
                ))
                await manager.broadcast(NotchStateMessage(state="expanded"))
                return denied_msg

        # Broadcast tool invocation
        await manager.broadcast(ToolCallMessage(id=call.id, tool=tool_name, args=args))

        try:
            result = await tool(**args)
            result_str = str(result)
            await manager.broadcast(ToolResultMessage(
                request_id=call.id, success=True, output=result_str
            ))
            await manager.broadcast(NotchStateMessage(state="expanded"))
            return result_str
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}", exc_info=True)
            err_str = str(e)
            await manager.broadcast(ToolResultMessage(
                request_id=call.id, success=False, error=err_str
            ))
            return f"Error: {err_str}"

    def _system_prompt(self) -> str:
        tool_lines = [
            f"- {t._tool_schema.name}: {t._tool_schema.description}"
            for t in TOOL_REGISTRY.values()
        ]
        return (
            "You are VELO, a smart local AI assistant running on Windows.\n"
            "You have access to tools to browse the web, run shell commands, search, and control the system.\n"
            "When the user asks you to do something, choose the right tool(s) and execute them.\n"
            "Be concise. If a tool requires permission, the user will be asked via the UI.\n\n"
            "Available tools:\n" + "\n".join(tool_lines)
        )


# Global singleton — set in main.py lifespan
_handler: MessageHandler | None = None


def set_handler(handler: MessageHandler):
    global _handler
    _handler = handler


async def handle_message(websocket: WebSocket, message):
    if _handler:
        await _handler.handle(websocket, message)
    else:
        logger.warning("handle_message called before handler was set")