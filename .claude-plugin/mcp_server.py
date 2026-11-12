#!/usr/bin/env python3
"""
WeRead Exporter MCP Server
Provides tools for exporting WeRead books.
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

# Add project root to path (parent of .claude-plugin directory)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from weread_exporter import utils


ALLOWED_FORMATS = frozenset({"epub", "txt", "md"})
SECRET_RE = re.compile(
    r"(?i)((?:cookie|token|session|wr_vid|skey|vid)\s*[=:]\s*)([^\s;,]+)"
)


def bounded_int(arguments, name, default, minimum, maximum):
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def sanitize_output(text):
    text = SECRET_RE.sub(r"\1[REDACTED]", text)
    return text[-8000:]


async def main():
    """MCP Server entry point"""
    # Read messages from stdin
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            message = json.loads(line.strip())
            await handle_message(message)
        except EOFError:
            break
        except Exception as e:
            logging.error(f"Error: {e}", exc_info=True)


async def handle_message(message):
    """Handle MCP messages"""
    if message.get("method") == "initialize":
        # Respond with server capabilities
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "serverInfo": {"name": "weread-exporter", "version": "0.2.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }
        print(json.dumps(response))
        sys.stdout.flush()

    elif message.get("method") == "tools/list":
        # List available tools
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "export_weread_book",
                        "description": "Export a WeRead book to specified format(s). Book ID can be obtained from: https://weread.qq.com/web/bookDetail/{book_id}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "book_id": {
                                    "type": "string",
                                    "description": "The WeRead book ID (e.g., 08232ac0720befa90825d88)",
                                },
                                "formats": {
                                    "type": "array",
                                    "description": "Output format(s)",
                                    "items": {
                                        "type": "string",
                                        "enum": ["epub", "txt", "md"],
                                    },
                                    "default": ["epub"],
                                },
                                "headless": {
                                    "type": "boolean",
                                    "description": "Run chrome in headless mode",
                                    "default": False,
                                },
                                "force_login": {
                                    "type": "boolean",
                                    "description": "Start the QR login flow when no saved session exists",
                                    "default": False,
                                },
                                "load_timeout": {
                                    "type": "integer",
                                    "description": "Load chapter page timeout in seconds",
                                    "default": 60,
                                },
                                "load_interval": {
                                    "type": "integer",
                                    "description": "Load chapter page interval in seconds",
                                    "default": 30,
                                },
                                "login_timeout": {
                                    "type": "integer",
                                    "minimum": 30,
                                    "maximum": 600,
                                    "default": 180,
                                },
                            },
                            "required": ["book_id"],
                        },
                    }
                ]
            },
        }
        print(json.dumps(response))
        sys.stdout.flush()

    elif message.get("method") == "tools/call":
        # Execute a tool
        await handle_tool_call(message)


async def handle_tool_call(message):
    """Handle tool execution"""
    tool_name = message.get("params", {}).get("name")
    arguments = message.get("params", {}).get("arguments", {})

    if tool_name == "export_weread_book":
        result = await export_weread_book(arguments)
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"content": [{"type": "text", "text": result}]},
        }
    else:
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    print(json.dumps(response))
    sys.stdout.flush()


async def export_weread_book(arguments):
    """Export a WeRead book"""
    book_id = arguments.get("book_id")
    try:
        utils.validate_book_id(book_id)
    except ValueError as exc:
        return f"Error: {exc}"

    # Validate formats independently of the JSON schema.
    formats = arguments.get("formats", ["epub"])
    if not isinstance(formats, list) or not formats:
        return "Error: formats must be a non-empty array"
    if any(not isinstance(fmt, str) or fmt not in ALLOWED_FORMATS for fmt in formats):
        return "Error: formats may contain only epub, txt, or md"
    formats = list(dict.fromkeys(formats))

    try:
        load_timeout = bounded_int(arguments, "load_timeout", 60, 10, 600)
        load_interval = bounded_int(arguments, "load_interval", 30, 0, 300)
        login_timeout = bounded_int(arguments, "login_timeout", 180, 30, 600)
    except ValueError as exc:
        return f"Error: {exc}"
    for boolean_name in ("headless", "force_login"):
        if boolean_name in arguments and not isinstance(arguments[boolean_name], bool):
            return f"Error: {boolean_name} must be a boolean"

    # Build command arguments
    cmd_args = ["-m", "weread_exporter", "-b", book_id]
    for fmt in formats:
        cmd_args.extend(["-o", fmt])

    # Login is explicit so ordinary exports cannot unexpectedly open a login flow.
    force_login = arguments.get("force_login", False)
    if force_login:
        cmd_args.append("--force-login")

    # Optional parameters
    if arguments.get("headless"):
        cmd_args.append("--headless")

    cmd_args.extend(["--load-timeout", str(load_timeout)])
    cmd_args.extend(["--load-interval", str(load_interval)])
    cmd_args.extend(["--login-timeout", str(login_timeout)])
    output_dir = Path(PROJECT_DIR, "output").resolve()
    cmd_args.extend(["--output-dir", str(output_dir)])

    # Execute the exporter
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            *cmd_args,
            cwd=PROJECT_DIR,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            output += stderr.decode("utf-8", errors="replace")
        output = sanitize_output(output)

        if process.returncode != 0:
            return f"Export failed (exit code {process.returncode}):\n{output}"

        # List exported files
        if output_dir.exists():
            files = [f.name for f in output_dir.iterdir() if f.is_file()]
            if files:
                output += "\n\nExported files:\n"
                for f in sorted(files):
                    fpath = output_dir / f
                    size = fpath.stat().st_size
                    size_mb = size / (1024 * 1024)
                    output += f"  - {f} ({size_mb:.2f} MB)\n"

        return f"Export completed!\n\n{output}"

    except Exception as e:
        return f"Error during export: {e}"


if __name__ == "__main__":
    asyncio.run(main())
