import logging
from velo_core.services.ollama import OllamaService
from velo_core.security import permission_gate
from velo_core.tools.base import TOOL_REGISTRY
from velo_core.websocket.manager import manager
from velo_core.models.schemas import ToolResultMessage, ToolCallMessage, TranscriptionMessage, NotchStateMessage

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self):
        self.ollama = OllamaService()

    async def process(self, user_input: str):
        await manager.broadcast(NotchStateMessage(state="expanded"))
        await manager.broadcast(TranscriptionMessage(text=user_input, final=True))

        tools = [tool._tool_schema for tool in TOOL_REGISTRY.values()]

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_input},
        ]

        try:
            response = await self.ollama.chat(messages, tools)

            if response.message.tool_calls:
                for call in response.message.tool_calls:
                    await self._execute_tool_call(call)
            else:
                await manager.broadcast(TranscriptionMessage(
                    text=response.message.content or "Done.", final=True
                ))
                await manager.broadcast(NotchStateMessage(state="idle"))

        except Exception as e:
            logger.error(f"Agent error: {e}")
            await manager.broadcast(TranscriptionMessage(text=f"Error: {str(e)}", final=True))
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

        if schema.requires_permission:
            allowed = await permission_gate.request_permission(
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