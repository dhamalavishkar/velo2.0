export type NotchState = 
  | 'idle' 
  | 'listening' 
  | 'expanded' 
  | 'permission' 
  | 'notification'
  | 'activation';

export type NotificationSentiment = 'ambient' | 'urgent' | 'media';

export interface NotchEvent {
  type: 'notch_state';
  state: NotchState;
}

export interface TranscriptionEvent {
  type: 'transcription';
  text: string;
  final: boolean;
}

export interface ToolCallEvent {
  type: 'tool_call';
  id: string;
  tool: string;
  args: Record<string, unknown>;
}

export interface PermissionRequestEvent {
  type: 'permission_request';
  id: string;
  tool: string;
  args: Record<string, unknown>;
  risk: 'low' | 'medium' | 'high';
  description: string;
}

export interface ToolResultEvent {
  type: 'tool_result';
  request_id: string;
  success: boolean;
  output?: string;
  error?: string;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export interface NotificationEvent {
  type: 'notification';
  id: string;
  summary: string;
  sentiment: NotificationSentiment;
}

export interface ActivationEvent {
  type: 'activation';
  phrase: string;
}

export type WSMessage =
  | NotchEvent
  | TranscriptionEvent
  | ToolCallEvent
  | PermissionRequestEvent
  | ToolResultEvent
  | ErrorEvent
  | NotificationEvent
  | ActivationEvent;

export interface PermissionRequest {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  risk: 'low' | 'medium' | 'high';
  description: string;
  timestamp: number;
}

export interface ToolStatus {
  id: string;
  tool: string;
  status: 'pending' | 'executing' | 'success' | 'error';
  output?: string;
  error?: string;
}

export interface NotificationItem {
  id: string;
  summary: string;
  sentiment: NotificationSentiment;
  timestamp: number;
}