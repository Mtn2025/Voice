"""
Configuration Utilities - Punto B3

Centralizes logic for managing configuration files (specifically .env).
Eliminates code duplication across dashboard endpoints.
"""

import re
from pathlib import Path
from typing import Any

from app.core.exceptions import ConfigurationError

# Define keys that are safe to update/expose via dashboard
# Using sets for faster lookup
VALID_KEYS = {
    # Browser Config
    "BROWSER_USE_TOKEN",
    "BROWSER_HEADLESS",
    "BROWSER_DISABLE_SECURITY",
    # Twilio Config
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    # Telnyx Config
    "TELNYX_API_KEY",
    "TELNYX_PUBLIC_KEY",
    # Core Config
    "SYSTEM_PROMPT",
    "VOICE_ID",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
    "GROQ_API_KEY",
    "GROQ_MODEL"
}

def update_env_file(updates: dict[str, Any], env_path: str = ".env") -> bool:
    """
    Updates the .env file with provided key-value pairs.
    Preserves existing structure and comments.

    Args:
        updates: Dictionary of keys and values to update.
        env_path: Path to the .env file.

    Returns:
        True if successful.

    Raises:
        ConfigurationError: If file update fails.
    """
    try:
        path = Path(env_path)
        if not path.exists():
            # Create if not exists
            path.touch()

        # Read existing content
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()

        new_lines = []
        updated_keys = set()

        # Process existing lines
        for line in lines:
            line_stripped = line.strip()
            # Skip empty lines or comments
            if not line_stripped or line_stripped.startswith("#"):
                new_lines.append(line)
                continue

            # Match assignments: KEY=VALUE
            match = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line_stripped)
            if match:
                key = match.group(1)
                if key in updates:
                    # Validate key security (optional safeguard)
                    # if key not in VALID_KEYS: ...

                    val = str(updates[key])
                    # Escape quotes if needed or just plain string
                    # Simple approach: If spaces, wrap in quotes?
                    # For now, simplistic replacement as used in original dashboard
                    new_lines.append(f"{key}={val}")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Append new keys that weren't in the file
        for key, val in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={val!s}")

        # Write back
        # Ensure trailing newline
        final_content = "\n".join(new_lines) + "\n"
        path.write_text(final_content, encoding="utf-8")

        return True

    except Exception as e:
        raise ConfigurationError(f"Failed to update .env file: {e!s}") from e

def read_env_file(env_path: str = ".env") -> dict[str, str]:
    """
    Reads the .env file and returns a dictionary of values.
    Useful for populating the dashboard without reloading the whole app config.
    """
    try:
        path = Path(env_path)
        if not path.exists():
            return {}

        config = {}
        content = path.read_text(encoding="utf-8")

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
            if match:
                key = match.group(1)
                val = match.group(2)
                # Remove potential wrapping quotes
                val = val.strip("'").strip('"')
                config[key] = val

        return config
    except Exception as e:
        raise ConfigurationError(f"Failed to read .env file: {e!s}")
