# MCP Confluence Server

A Model Context Protocol (MCP) server that fetches content from Confluence pages and converts them to markdown format.

## Features

- Fetch content from Confluence pages using the REST API
- Automatic conversion of HTML content to Markdown format
- Support for both stdio and SSE transports
- Authentication via Bearer token
- List all pages in a specified Confluence space
- Read individual page content with HTML to Markdown conversion

## Installation

We recommend using [uv](https://docs.astral.sh/uv/) to install and run the server:

```bash
# Using stdio transport (default)
uv run mcp-confluence --confluence-url "https://your-confluence.example.com" --space-key "SPACE"

# Using SSE transport with authentication
uv run mcp-confluence \
  --transport sse \
  --port 8000 \
  --confluence-url "https://your-confluence.example.com" \
  --space-key "SPACE" \
  --auth-token "your-token"
```

### Command Line Options

- `--confluence-url`: (Required) Base URL of your Confluence instance
- `--space-key`: (Required) The Confluence space key to fetch content from
- `--auth-token`: (Optional) Authentication token for Confluence API
- `--transport`: (Optional) Transport type: "stdio" or "sse" (default: "stdio")
- `--port`: (Optional) Port to listen on for SSE transport (default: 8000)

## Example

Using the MCP client, you can retrieve Confluence pages like this:

```python
import asyncio
from mcp.types import AnyUrl
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    async with stdio_client(
        StdioServerParameters(
            command="uv",
            args=[
                "run",
                "mcp-confluence",
                "--confluence-url",
                "https://your-confluence.example.com",
                "--space-key",
                "SPACE"
            ]
        )
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available pages
            resources = await session.list_resources()
            print(resources)

            # Get a specific page content (returns markdown)
            resource = await session.read_resource(
                AnyUrl("confluence:///SPACE/Welcome Page")
            )
            print(resource)

asyncio.run(main())
```

## Resource URI Format

The server uses the following URI format for Confluence resources:
```
confluence:///{space_key}/{page_title}
```

For example:
```
confluence:///SPACE/Welcome Page
```

## Implementation Details

The server implements two main MCP capabilities:

1. `list_resources()`: Lists all available pages in the specified Confluence space
2. `read_resource()`: Fetches and converts a specific page's content to Markdown

The HTML to Markdown conversion preserves:
- Links
- Images
- Tables
- Lists
- Headers
- Code blocks
- Other formatting elements

## Dependencies

The server requires the following Python packages:
- `mcp`: Model Context Protocol SDK
- `httpx`: For async HTTP requests to Confluence API
- `beautifulsoup4`: For HTML parsing and cleaning
- `html2text`: For HTML to Markdown conversion
- `anyio`: For async I/O operations
- `click`: For command line interface

## License

MIT License - See LICENSE file for details