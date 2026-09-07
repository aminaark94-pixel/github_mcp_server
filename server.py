import logging

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

# ... (baaki saari Pydantic models, enums, aur Git functions same rahenge) ...

async def serve(repository: Path | None) -> None:
    logger = logging.getLogger(__name__)

    if repository is not None:
        try:
            git.Repo(repository)
            logger.info(f"Using repository at {repository}")
        except git.InvalidGitRepositoryError:
            logger.error(f"{repository} is not a valid Git repository")
            return

    server = Server("mcp-git")

    # ... (list_tools, list_repos, aur call_tool decorator handlers bilkul same rahenge) ...

    # Setup SSE Transport
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_ssess(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )

    # Starlette App Routing
    app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages/", endpoint=sse.handle_post_message, methods=["POST"]),
        ],
    )

    # Run Server with Uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()

if __name__ == "__main__":
    import asyncio
    import sys

    repo_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(serve(repo_arg))
