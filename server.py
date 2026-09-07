"""
Minimal Remote MCP Server (from scratch) — Streamable HTTP transport.

Built to work as a Claude "custom connector": deploy this on Render as a
Web Service, then paste https://<your-app>.onrender.com/mcp into
Claude's "Remote MCP server URL" field.
"""

import os
import logging
import subprocess

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- BUILD MARKER -----------------------------------------------------
# Look for this exact line in Render's logs right after "Running 'python
# server.py'". If you don't see it, Render is still running old/cached
# code — the fix below hasn't actually been deployed yet.
logger.info("BUILD_MARKER: server.py v3 (dns-rebinding-protection DISABLED)")
# -------------------------------------------------------------------------

REPO_PATH = os.environ.get("GIT_REPO_PATH", ".")

# DNS-rebinding protection only trusts "localhost" by default, which is
# what caused the 421 "Invalid Host header" errors against the public
# Render URL. This server is not browser-facing, so we disable that check.
mcp = FastMCP(
    "mcp-git",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


def run_git(args: list[str], repo_path: str = REPO_PATH) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip() or "(no output)"
    except Exception as e:
        logger.exception("git command failed: %s", args)
        return f"Error running git {' '.join(args)}: {e}"


@mcp.tool()
def ping() -> str:
    """Simple health-check tool — call this first to confirm the connector works."""
    return "pong"


@mcp.tool()
def git_status(repo_path: str = REPO_PATH) -> str:
    """Show the working tree status of a git repository."""
    return run_git(["status"], repo_path)


@mcp.tool()
def git_log(repo_path: str = REPO_PATH, max_count: int = 10) -> str:
    """Show recent commit log entries."""
    return run_git(
        ["log", f"-{max_count}", "--pretty=format:%h | %an | %ad | %s", "--date=short"],
        repo_path,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info("Starting mcp-git streamable-http server on 0.0.0.0:%s", port)

    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port

    mcp.run(transport="streamable-http")
