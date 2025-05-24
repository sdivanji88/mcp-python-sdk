# MCP Image OCR Server

An MCP server that processes images, extracts text using OCR, and provides tools for using the extracted text as context in LLM conversations.

## Features

- Download images from URLs or load from local filesystem
- Extract text from images using OCR (Tesseract)
- Provide tools to use extracted text as context for LLM chats
- Include common prompts for image text analysis

## Requirements

- Python 3.9+
- Tesseract OCR installed on your system

### Installing Tesseract OCR

#### macOS:
```
brew install tesseract
```

#### Ubuntu/Debian:
```
sudo apt update
sudo apt install -y tesseract-ocr
```

#### Windows:
Install from the official installer: https://github.com/UB-Mannheim/tesseract/wiki

## Installation

```bash
# Clone the repository
git clone https://github.com/modelcontextprotocol/python-sdk.git
cd python-sdk/examples/servers/image-mcp

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

### Running the server

```bash
# Run with stdio transport (default)
python -m mcp_image_ocr

# Or use the installed script
mcp-image-ocr

# Run with SSE transport (requires optional dependencies)
pip install -e ".[sse]"
mcp-image-ocr --transport sse --port 8000
```

### Client Connection

Connect to the server using any MCP client:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="mcp-image-ocr",
    args=[],
    env=None
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # Use the server's capabilities
            # ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
```

## Available Tools

The server exposes these MCP tools:

- `downloadImageFromUrl`: Download an image from a URL
- `loadImageFromPath`: Load an image from a local file path
- `extractTextFromImage`: Extract text from an image using OCR
- `useTextAsContext`: Use extracted text as context for LLM

## Available Prompts

The server provides these prompt templates:

- `analyzeImageContent`: Analyze the content of an image based on extracted text
- `extractInformation`: Extract specific information from image text
- `summarizeImageText`: Summarize the text extracted from an image

## Example Workflow

1. Download an image:
   ```python
   result = await session.call_tool("downloadImageFromUrl", {"url": "https://example.com/image.jpg"})
   resource_id = result[0].text.split("Resource ID: ")[1]
   ```

2. Extract text from the image:
   ```python
   result = await session.call_tool("extractTextFromImage", {"resource_id": resource_id})
   ```

3. Use the extracted text with a prompt:
   ```python
   prompt = await session.get_prompt("analyzeImageContent", {"resource_id": resource_id})
   ```

## Configuration

The server can be configured using environment variables:

- `IMAGE_MCP_DEFAULT_EXTRACTOR`: Default text extractor to use (default: "tesseract")
- `IMAGE_MCP_CACHE_DIR`: Directory for caching processed images (default: "./.image_cache")
- `IMAGE_MCP_MAX_IMAGE_SIZE`: Maximum allowed image size in bytes (default: 10MB)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 