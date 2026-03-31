#!/usr/bin/env python3
"""
Self-configuration script for Gemini Runner MCP server.

Automatically adds the gemini-runner MCP server to:
1. Claude Desktop config (claude_desktop_config.json)
2. GitHub Copilot CLI config (mcp-config.json)
"""
import json
import os
import sys
import tempfile
from pathlib import Path


def get_claude_config_path():
    """Determine Claude Desktop config path based on OS."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            raise RuntimeError("APPDATA environment variable not found")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_copilot_config_path():
    """Determine Copilot CLI MCP config path."""
    return Path.home() / ".copilot" / "mcp-config.json"


def setup_config_file(config_path, server_script, app_name):
    """Add gemini-runner to an MCP config file."""
    print(f"\n📍 {app_name} config: {config_path}")
    
    # Load or create config
    if config_path.exists():
        print(f"   📖 Reading existing config...")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            backup_path = config_path.with_suffix(config_path.suffix + ".bak")
            config_path.replace(backup_path)
            print(f"   ⚠️  Existing config is invalid JSON. Backed up to: {backup_path}")
            config = {}
    else:
        print(f"   📝 Creating new config file...")
        config = {}
        config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add gemini-runner server
    server_config = {
        "command": "python",
        "args": [str(server_script)],
        "description": "Isolated Gemini CLI runner for audits with no context pollution"
    }
    
    if "gemini-runner" in config["mcpServers"]:
        print(f"   ⚠️  gemini-runner already exists, updating...")
    else:
        print(f"   ✅ Adding gemini-runner to config...")
    
    config["mcpServers"]["gemini-runner"] = server_config
    
    # Atomic write to avoid partial/corrupted file on crash.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(config_path.parent),
        delete=False,
        suffix=".tmp",
    ) as tf:
        json.dump(config, tf, indent=2)
        temp_path = Path(tf.name)
    temp_path.replace(config_path)
    
    print(f"   ✅ Configuration written successfully!")
    return True


def setup_mcp_config():
    """Add gemini-runner to all detected MCP-compatible apps."""
    server_script = Path(__file__).parent.absolute() / "mcp_server.py"
    
    print(f"📍 MCP server script: {server_script}")
    
    if not server_script.exists():
        print(f"❌ Error: mcp_server.py not found at {server_script}")
        return 1
    
    success_count = 0
    
    # Try Claude Desktop
    try:
        claude_path = get_claude_config_path()
        if setup_config_file(claude_path, server_script, "Claude Desktop"):
            success_count += 1
    except Exception as e:
        print(f"\n⚠️  Could not configure Claude Desktop: {e}")
    
    # Try Copilot CLI
    try:
        copilot_path = get_copilot_config_path()
        if setup_config_file(copilot_path, server_script, "GitHub Copilot CLI"):
            success_count += 1
    except Exception as e:
        print(f"\n⚠️  Could not configure Copilot CLI: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"✅ Successfully configured {success_count} application(s)")
    print("="*60)
    print()
    print("Next steps:")
    print("  • Restart Claude Desktop (if configured)")
    print("  • Restart Copilot CLI session (if configured)")
    print("  • The 'gemini_audit' tool should now be available")
    print()
    print("Test it with:")
    print("  'Please use gemini_audit to analyze this repository'")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(setup_mcp_config())
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
