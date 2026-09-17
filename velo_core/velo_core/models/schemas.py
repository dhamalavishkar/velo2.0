from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class NotchState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    EXPANDED = "expanded"
    PERMISSION = "permission"
    NOTIFICATION = "notification"
    ACTIVATION = "activation"


class NotificationSentiment(str, Enum):
    AMBIENT = "ambient"
    URGENT = "urgent"
    MEDIA = "media"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WSMessageType(str, Enum):
    NOTCH_STATE = "notch_state"
    TRANSCRIPTION = "transcription"
    TOOL_CALL = "tool_call"
    PERMISSION_REQUEST = "permission_request"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    WAKE_WORD_DETECTED = "wake_word_detected"
    AUDIO_CHUNK = "audio_chunk"
    PERMISSION_RESPONSE = "permission_response"
    NOTIFICATION = "notification"
    ACTIVATION = "activation"


class BaseWSMessage(BaseModel):
    type: WSMessageType


class NotchStateMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.NOTCH_STATE
    state: NotchState


class TranscriptionMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.TRANSCRIPTION
    text: str
    final: bool = False


class ToolCallMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.TOOL_CALL
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool: str
    args: dict[str, Any]


class PermissionRequestMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.PERMISSION_REQUEST
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool: str
    args: dict[str, Any]
    risk: RiskLevel
    description: str


class ToolResultMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.TOOL_RESULT
    request_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class ErrorMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.ERROR
    message: str


class WakeWordDetectedMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.WAKE_WORD_DETECTED


class AudioChunkMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.AUDIO_CHUNK
    data: str  # base64 encoded PCM16


class PermissionResponseMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.PERMISSION_RESPONSE
    request_id: str
    allowed: bool


class NotificationMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.NOTIFICATION
    id: str = Field(default_factory=lambda: str(uuid4()))
    summary: str
    sentiment: NotificationSentiment


class ActivationMessage(BaseWSMessage):
    type: WSMessageType = WSMessageType.ACTIVATION
    phrase: str


WSMessage = (
    NotchStateMessage
    | TranscriptionMessage
    | ToolCallMessage
    | PermissionRequestMessage
    | ToolResultMessage
    | ErrorMessage
    | WakeWordDetectedMessage
    | AudioChunkMessage
    | PermissionResponseMessage
    | NotificationMessage
    | ActivationMessage
)


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]
    requires_permission: bool = False
    risk_level: RiskLevel = RiskLevel.LOW


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    id: str = Field(default_factory=lambda: str(uuid4()))


class ToolResult(BaseModel):
    tool_call_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None