from enum import Enum
from typing import Any, Literal, Optional, Annotated, Union
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
    USER_INPUT = "user_input"


class NotchStateMessage(BaseModel):
    type: Literal[WSMessageType.NOTCH_STATE] = WSMessageType.NOTCH_STATE
    state: NotchState


class TranscriptionMessage(BaseModel):
    type: Literal[WSMessageType.TRANSCRIPTION] = WSMessageType.TRANSCRIPTION
    text: str
    final: bool = False


class ToolCallMessage(BaseModel):
    type: Literal[WSMessageType.TOOL_CALL] = WSMessageType.TOOL_CALL
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool: str
    args: dict[str, Any]


class PermissionRequestMessage(BaseModel):
    type: Literal[WSMessageType.PERMISSION_REQUEST] = WSMessageType.PERMISSION_REQUEST
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool: str
    args: dict[str, Any]
    risk: RiskLevel
    description: str


class ToolResultMessage(BaseModel):
    type: Literal[WSMessageType.TOOL_RESULT] = WSMessageType.TOOL_RESULT
    request_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class ErrorMessage(BaseModel):
    type: Literal[WSMessageType.ERROR] = WSMessageType.ERROR
    message: str


class WakeWordDetectedMessage(BaseModel):
    type: Literal[WSMessageType.WAKE_WORD_DETECTED] = WSMessageType.WAKE_WORD_DETECTED


class AudioChunkMessage(BaseModel):
    type: Literal[WSMessageType.AUDIO_CHUNK] = WSMessageType.AUDIO_CHUNK
    data: str  # base64 encoded PCM16


class PermissionResponseMessage(BaseModel):
    type: Literal[WSMessageType.PERMISSION_RESPONSE] = WSMessageType.PERMISSION_RESPONSE
    request_id: str
    allowed: bool


class NotificationMessage(BaseModel):
    type: Literal[WSMessageType.NOTIFICATION] = WSMessageType.NOTIFICATION
    id: str = Field(default_factory=lambda: str(uuid4()))
    summary: str
    sentiment: NotificationSentiment


class ActivationMessage(BaseModel):
    type: Literal[WSMessageType.ACTIVATION] = WSMessageType.ACTIVATION
    phrase: str


class UserInputMessage(BaseModel):
    """Client sends this to submit text without wake word (testing / text mode)."""
    type: Literal[WSMessageType.USER_INPUT] = WSMessageType.USER_INPUT
    text: str


# Discriminated union — Pydantic resolves the correct class via the `type` field
WSMessage = Annotated[
    Union[
        NotchStateMessage,
        TranscriptionMessage,
        ToolCallMessage,
        PermissionRequestMessage,
        ToolResultMessage,
        ErrorMessage,
        WakeWordDetectedMessage,
        AudioChunkMessage,
        PermissionResponseMessage,
        NotificationMessage,
        ActivationMessage,
        UserInputMessage,
    ],
    Field(discriminator="type"),
]


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