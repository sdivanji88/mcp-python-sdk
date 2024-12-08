import anyio
import click
import httpx
import mcp.types as types
from mcp.server import AnyUrl, Server
from typing import Optional
from bs4 import BeautifulSoup
import html2text

class ConfluenceClient:
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Accept": "application/json",
        }
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self.html_converter = html2text.HTML2Text()
        self.html_converter.body_width = 0  # Don't wrap text
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_tables = False

    def convert_html_to_markdown(self, html_content: str) -> str:
        # First clean up the HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        clean_html = str(soup)
        # Convert to markdown
        return self.html_converter.handle(clean_html)

    async def get_page_content(self, space_key: str, title: str) -> dict:
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "body.view",
            "type": "page"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rest/api/content",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                raise ValueError(f"Page not found: {title} in space {space_key}")
            
            page = data["results"][0]
            # Convert HTML content to Markdown
            if "body" in page and "view" in page["body"]:
                html_content = page["body"]["view"]["value"]
                page["body"]["view"]["value"] = self.convert_html_to_markdown(html_content)
                
            return page

    async def list_pages(self, space_key: str) -> list[dict]:
        params = {
            "spaceKey": space_key,
            "type": "page",
            "status": "current",
            "expand": "title"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rest/api/content",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()["results"]

@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
@click.option(
    "--confluence-url",
    required=True,
    help="Base URL of the Confluence instance",
)
@click.option(
    "--auth-token",
    help="Authentication token for Confluence API",
)
@click.option(
    "--space-key",
    required=True,
    help="Confluence space key to fetch content from",
)
def main(port: int, transport: str, confluence_url: str, auth_token: Optional[str], space_key: str) -> int:
    app = Server("mcp-confluence")
    confluence = ConfluenceClient(confluence_url, auth_token)

    @app.list_resources()
    async def list_resources() -> list[types.Resource]:
        pages = await confluence.list_pages(space_key)
        return [
            types.Resource(
                uri=AnyUrl(f"confluence:///{space_key}/{page['title']}"),
                name=page['title'],
                description=f"Confluence page: {page['title']}",
                mimeType="text/html",
            )
            for page in pages
        ]

    @app.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        assert uri.path is not None
        # Extract space key and title from path
        parts = uri.path.lstrip('/').split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid Confluence URI: {uri}")
        
        space_key, title = parts
        
        try:
            page = await confluence.get_page_content(space_key, title)
            return page["body"]["view"]["value"]
        except Exception as e:
            raise ValueError(f"Failed to fetch Confluence page: {e}")

    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages", endpoint=handle_messages, methods=["POST"]),
            ],
        )

        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0
