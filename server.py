"""
Remote MCP Git Server — Streamable HTTP transport (for Render deployment)

This replaces a stdio-based mcp-server-git style script with one that
binds to Render's $PORT and speaks MCP over HTTP, so it can be added
to Claude as a "Remote MCP server URL" custom connector.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_PATH = os.environ.get("GIT_REPO_PATH", ".")

# The MCP SDK's DNS-rebinding protection only trusts "localhost" by default,
# so every real request coming through Render's public domain gets rejected
# with 421 "Invalid Host header". "*" is NOT a supported wildcard for
# allowed_hosts (only "host:*" for any port, or "*.example.com" for
# subdomains) — so the only reliable fix here is to turn the check off.
# This server isn't browser-facing, so DNS rebinding isn't a real risk here.
mcp = FastMCP(
    "mcp-git",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


def run_git(args: list[str], repo_path: str = REPO_PATH) -> str:
    """Run a git command inside repo_path and return combined output."""
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
def git_status(repo_path: str = REPO_PATH) -> str:
    """Show the working tree status of a git repository."""
    return run_git(["status"], repo_path)


@mcp.tool()
def git_diff_unstaged(repo_path: str = REPO_PATH, context_lines: int = 3) -> str:
    """Show changes in the working directory that are not yet staged."""
    return run_git(["diff", f"--unified={context_lines}"], repo_path)


@mcp.tool()
def git_diff_staged(repo_path: str = REPO_PATH, context_lines: int = 3) -> str:
    """Show changes that are staged for the next commit."""
    return run_git(["diff", "--staged", f"--unified={context_lines}"], repo_path)


@mcp.tool()
def git_diff(repo_path: str, target: str, context_lines: int = 3) -> str:
    """Show differences between the current state and a target branch/commit."""
    return run_git(["diff", f"--unified={context_lines}", target], repo_path)


@mcp.tool()
def git_add(repo_path: str, files: list[str]) -> str:
    """Stage the given file paths."""
    return run_git(["add"] + files, repo_path)


@mcp.tool()
def git_commit(repo_path: str, message: str) -> str:
    """Commit staged changes with the given message."""
    return run_git(["commit", "-m", message], repo_path)


@mcp.tool()
def git_reset(repo_path: str = REPO_PATH) -> str:
    """Unstage all currently staged changes."""
    return run_git(["reset"], repo_path)


@mcp.tool()
def git_log(repo_path: str = REPO_PATH, max_count: int = 10) -> str:
    """Show recent commit log entries."""
    return run_git(["log", f"-{max_count}", "--pretty=format:%h | %an | %ad | %s", "--date=short"], repo_path)


@mcp.tool()
def git_create_branch(repo_path: str, branch_name: str, base_branch: Optional[str] = None) -> str:
    """Create a new branch, optionally from a given base branch."""
    args = ["branch", branch_name]
    if base_branch:
        args.append(base_branch)
    return run_git(args, repo_path)


@mcp.tool()
def git_checkout(repo_path: str, branch_name: str) -> str:
    """Switch to the given branch."""
    return run_git(["checkout", branch_name], repo_path)


@mcp.tool()
def git_show(repo_path: str, revision: str) -> str:
    """Show the contents / metadata of a given commit."""
    return run_git(["show", revision], repo_path)


@mcp.tool()
def git_branch(repo_path: str = REPO_PATH, branch_type: str = "local") -> str:
    """List git branches. branch_type: 'local', 'remote', or 'all'."""
    flag = {"local": [], "remote": ["-r"], "all": ["-a"]}.get(branch_type, [])
    return run_git(["branch"] + flag, repo_path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info("Starting mcp-git streamable-http server on 0.0.0.0:%s", port)

    # FastMCP's streamable-http transport reads host/port from these settings.
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port

    # This serves MCP over HTTP at http://<host>:<port>/mcp
    mcp.run(transport="streamable-http")
