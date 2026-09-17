import asyncio
import uuid
import logging
from typing import Any, Callable, Awaitable
from velo_core.models.schemas import PermissionRequestMessage, RiskLevel

logger = logging.getLogger(__name__)

BroadcastFunc = Callable[[PermissionRequestMessage], Awaitable[None]]


class PermissionGate:
    def __init__(self, broadcast: BroadcastFunc | None = None):
        self.pending: dict[str, asyncio.Future] = {}
        self._broadcast = broadcast

    def set_broadcast(self, broadcast: BroadcastFunc):
        self._broadcast = broadcast

    async def request_permission(
        self, tool: str, args: dict[str, Any], risk: RiskLevel
    ) -> bool:
        if not self._broadcast:
            raise RuntimeError("PermissionGate broadcast function not set")

        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending[request_id] = future

        description = self._generate_description(tool, args)

        await self._broadcast(PermissionRequestMessage(
            id=request_id,
            tool=tool,
            args=args,
            risk=risk,
            description=description,
        ))

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            logger.info(f"Permission {request_id}: {'granted' if result else 'denied'}")
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Permission {request_id}: timed out")
            return False
        finally:
            self.pending.pop(request_id, None)

    def resolve(self, request_id: str, allowed: bool):
        if request_id in self.pending:
            self.pending[request_id].set_result(allowed)

    def _generate_description(self, tool: str, args: dict[str, Any]) -> str:
        descriptions = {
            "run_shell": f"Run shell command: {args.get('command', '')} {' '.join(args.get('args', []))}",
            "set_clipboard": f"Set clipboard to: {str(args.get('text', ''))[:50]}...",
            "open_url": f"Open URL: {args.get('url', '')}",
            "click_element": f"Click element: {args.get('selector', '')}",
            "type_text": f"Type text into: {args.get('selector', '')}",
        }
        return descriptions.get(tool, f"Execute {tool}")


permission_gate = PermissionGate()