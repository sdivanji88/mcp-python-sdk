# MCP Confluence Server

This MCP server allows you to access Confluence pages as resources, automatically converting them from HTML to Markdown.

## Installation

```bash
# Clone the repository and navigate to this directory
cd examples/servers/simple-confluence

# Install using uv
uv pip install -e .
```

## Required Dependencies

The server depends on:
- anyio
- click
- httpx
- mcp
- beautifulsoup4
- html2text

All dependencies are automatically installed with the package.

## Usage

Run the server with the required Confluence parameters:

```bash
mcp-confluence --confluence-url="https://your-confluence-instance.atlassian.net" \
               --space-key="YOURSPACE" \
               --auth-token="your-api-token"
```

### Options

- `--confluence-url`: (Required) Base URL of your Confluence instance
- `--space-key`: (Required) Confluence space key to fetch content from
- `--auth-token`: (Optional) Authentication token for Confluence API
- `--transport`: Transport type, choose from "stdio" (default) or "sse"
- `--port`: Port to listen on when using SSE transport (default: 8000)

## Accessing Resources

The server exposes Confluence pages as resources with URIs in the format:
```
confluence:///SPACE_KEY/PAGE_TITLE
```

When accessed, the page content is automatically converted from HTML to Markdown format.