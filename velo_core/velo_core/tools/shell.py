import subprocess
import logging
from typing import Optional
from velo_core.tools.base import tool, register_tool

logger = logging.getLogger(__name__)

# Pre-defined safe commands for prototype
ALLOWED_COMMANDS = {
    "notepad": ["notepad.exe"],
    "calc": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe", "/c"],
    "powershell": ["powershell.exe", "-Command"],
    "dir": ["cmd.exe", "/c", "dir"],
    "ls": ["cmd.exe", "/c", "dir"],
    "echo": ["cmd.exe", "/c", "echo"],
    "type": ["cmd.exe", "/c", "type"],
    "copy": ["cmd.exe", "/c", "copy"],
    "move": ["cmd.exe", "/c", "move"],
    "del": ["cmd.exe", "/c", "del"],
    "mkdir": ["cmd.exe", "/c", "mkdir"],
    "rmdir": ["cmd.exe", "/c", "rmdir"],
}


@tool(
    name="run_shell",
    description="Run a shell command from the allowed list. Available: notepad, calc, explorer, cmd, powershell, dir, echo, type, copy, move, del, mkdir, rmdir",
    requires_permission=True,
    risk_level="high",
)
async def run_shell(command: str, args: Optional[list[str]] = None) -> str:
    if command not in ALLOWED_COMMANDS:
        return f"Command '{command}' not allowed. Allowed: {', '.join(ALLOWED_COMMANDS.keys())}"

    base_cmd = ALLOWED_COMMANDS[command]
    if args:
        full_cmd = base_cmd + args
    else:
        full_cmd = base_cmd

    try:
        logger.info(f"Running shell command: {full_cmd}")
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nStderr: {result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return output.strip() or "Command executed successfully (no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except Exception as e:
        logger.error(f"Shell command error: {e}")
        return f"Error: {str(e)}"


@tool(
    name="get_clipboard",
    description="Get text from Windows clipboard",
    requires_permission=False,
)
async def get_clipboard() -> str:
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return str(data) if data else "Clipboard empty"
    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return f"Error reading clipboard: {str(e)}"


@tool(
    name="set_clipboard",
    description="Set text to Windows clipboard",
    requires_permission=True,
    risk_level="low",
)
async def set_clipboard(text: str) -> str:
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
        win32clipboard.CloseClipboard()
        return f"Clipboard set to: {text[:50]}..."
    except Exception as e:
        logger.error(f"Clipboard write error: {e}")
        return f"Error writing clipboard: {str(e)}"


for tool_func in [run_shell, get_clipboard, set_clipboard]:
    register_tool(tool_func)