from functools import wraps
from typing import Callable, Any, get_type_hints
from pydantic import BaseModel, Field
from velo_core.models.schemas import ToolSchema, RiskLevel


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


def tool(
    name: str,
    description: str,
    requires_permission: bool = False,
    risk_level: RiskLevel = RiskLevel.LOW,
):
    """Decorator to register a tool with schema."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            return await func(*args, **kwargs)

        # Build JSON schema from function signature
        hints = get_type_hints(func)
        properties = {}
        required = []

        for param_name, param_type in hints.items():
            if param_name == "return":
                continue
            properties[param_name] = _type_to_json_schema(param_type)
            required.append(param_name)

        schema = ToolSchema(
            name=name,
            description=description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
            requires_permission=requires_permission,
            risk_level=risk_level,
        )

        wrapper._tool_schema = schema
        return wrapper

    return decorator


def _type_to_json_schema(py_type: type) -> dict:
    """Convert Python type to JSON schema."""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    return type_map.get(py_type, {"type": "string"})


# Global registry
TOOL_REGISTRY: dict[str, Callable] = {}


def register_tool(func: Callable) -> Callable:
    """Register a decorated tool function."""
    if hasattr(func, "_tool_schema"):
        TOOL_REGISTRY[func._tool_schema.name] = func
    return func