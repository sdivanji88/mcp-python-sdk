"""MCP server for image text extraction."""

import anyio
import os
import json
import asyncio
import click
import mcp.types as types
from typing import Union
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

from mcp_image_ocr.resource_manager import ResourceManager
from mcp_image_ocr.factories import PromptTemplateFactory


class ImageOcrServer:
    """MCP server for image text extraction."""
    
    def __init__(self, name: str = "image-ocr-server"):
        """Initialize the server."""
        self.name = name
        self.server = Server(name)
        self.resource_manager = ResourceManager()
        
        # Register MCP handlers
        self._register_tools()
        self._register_prompts()
        self._register_resources()
    
    def _register_tools(self):
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="downloadImageFromUrl",
                    description="Download an image from a URL",
                    inputSchema={
                        "type": "object",
                        "required": ["url"],
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL of the image to download",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="loadImageFromPath",
                    description="Load an image from a local file path",
                    inputSchema={
                        "type": "object",
                        "required": ["path"],
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Local file path to the image",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="extractTextFromImage",
                    description="Extract text from an image",
                    inputSchema={
                        "type": "object",
                        "required": ["resource_id"],
                        "properties": {
                            "resource_id": {
                                "type": "string",
                                "description": "Resource ID of the image",
                            },
                            "extractor": {
                                "type": "string",
                                "description": "Text extractor to use (tesseract or azure)",
                                "enum": ["tesseract", "azure"],
                                "default": "tesseract",
                            }
                        },
                    },
                ),
                types.Tool(
                    name="useTextAsContext",
                    description="Use extracted text as context for LLM",
                    inputSchema={
                        "type": "object",
                        "required": ["resource_id"],
                        "properties": {
                            "resource_id": {
                                "type": "string",
                                "description": "Resource ID of the image with extracted text",
                            }
                        },
                    },
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Call a tool."""
            if name == "downloadImageFromUrl":
                if "url" not in arguments:
                    raise ValueError("Missing required argument 'url'")
                
                try:
                    resource_id = await self.resource_manager.add_image_from_url(arguments["url"])
                    return [types.TextContent(
                        type="text",
                        text=f"Image downloaded successfully. Resource ID: {resource_id}"
                    )]
                except Exception as e:
                    raise ValueError(f"Failed to download image: {str(e)}")
            
            elif name == "loadImageFromPath":
                if "path" not in arguments:
                    raise ValueError("Missing required argument 'path'")
                
                try:
                    resource_id = await self.resource_manager.add_image_from_path(arguments["path"])
                    return [types.TextContent(
                        type="text",
                        text=f"Image loaded successfully. Resource ID: {resource_id}"
                    )]
                except Exception as e:
                    raise ValueError(f"Failed to load image: {str(e)}")
            
            elif name == "extractTextFromImage":
                if "resource_id" not in arguments:
                    raise ValueError("Missing required argument 'resource_id'")
                
                extractor = arguments.get("extractor", "tesseract")
                
                try:
                    result = await self.resource_manager.extract_text_from_image(
                        arguments["resource_id"], extractor
                    )
                    
                    return [types.TextContent(
                        type="text",
                        text=(
                            f"Text extracted successfully with confidence {result['confidence']:.2f}%.\n\n"
                            f"Extracted text:\n{result['text']}"
                        )
                    )]
                except Exception as e:
                    raise ValueError(f"Failed to extract text: {str(e)}")
            
            elif name == "useTextAsContext":
                if "resource_id" not in arguments:
                    raise ValueError("Missing required argument 'resource_id'")
                
                try:
                    extracted_text = self.resource_manager.get_extracted_text(arguments["resource_id"])
                    if not extracted_text:
                        # Try extracting text if it hasn't been done yet
                        try:
                            result = await self.resource_manager.extract_text_from_image(arguments["resource_id"])
                            extracted_text = result["text"]
                        except Exception as e:
                            # If extraction fails, use a placeholder message
                            extracted_text = "Unable to extract text from this image. Please ensure the image contains readable text."
                    
                    # Create an embedded resource with the extracted text
                    return [
                        types.EmbeddedResource(
                            type="resource",
                            resource=types.TextResourceContents(
                                uri=f"mcp:///resource/{arguments['resource_id']}",
                                mimeType="text/plain",
                                text=extracted_text
                            )
                        )
                    ]
                except Exception as e:
                    # Return a generic error message as embedded resource
                    return [
                        types.EmbeddedResource(
                            type="resource",
                            resource=types.TextResourceContents(
                                uri=f"mcp:///resource/error",
                                mimeType="text/plain",
                                text=f"Error retrieving text from the resource: {str(e)}"
                            )
                        )
                    ]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    def _register_prompts(self):
        """Register MCP prompts."""
        
        @self.server.list_prompts()
        async def list_prompts() -> list[types.Prompt]:
            """List available prompts."""
            return [
                types.Prompt(
                    name="analyzeImageContent",
                    description="Analyze the content of an image based on extracted text",
                    arguments=[
                        types.PromptArgument(
                            name="resource_id",
                            description="Resource ID of the image",
                            required=True
                        ),
                        types.PromptArgument(
                            name="analysis_type",
                            description="Type of analysis to perform",
                            required=False
                        )
                    ]
                ),
                types.Prompt(
                    name="extractInformation",
                    description="Extract specific information from image text",
                    arguments=[
                        types.PromptArgument(
                            name="resource_id",
                            description="Resource ID of the image",
                            required=True
                        ),
                        types.PromptArgument(
                            name="information_type",
                            description="Type of information to extract",
                            required=True
                        )
                    ]
                ),
                types.Prompt(
                    name="summarizeImageText",
                    description="Summarize the text extracted from an image",
                    arguments=[
                        types.PromptArgument(
                            name="resource_id",
                            description="Resource ID of the image",
                            required=True
                        ),
                        types.PromptArgument(
                            name="length",
                            description="Desired summary length",
                            required=False
                        )
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(
            name: str, arguments: dict[str, str] | None
        ) -> types.GetPromptResult:
            """Get a prompt with arguments."""
            if not arguments:
                raise ValueError("Missing required arguments")
            
            if "resource_id" not in arguments:
                raise ValueError("Missing required argument 'resource_id'")
            
            # Get the extracted text for the resource
            try:
                extracted_text = self.resource_manager.get_extracted_text(arguments["resource_id"])
                if not extracted_text:
                    # Try extracting text if it hasn't been done yet
                    try:
                        result = await self.resource_manager.extract_text_from_image(arguments["resource_id"])
                        extracted_text = result["text"] 
                    except Exception as e:
                        # If extraction fails, use a placeholder message
                        extracted_text = "Unable to extract text from this image. Please ensure the image contains readable text."
            except Exception as e:
                # Use a placeholder message if the resource doesn't exist or other errors occur
                extracted_text = "Error retrieving text from the resource."
            
            # Process the prompt based on name
            if name == "analyzeImageContent":
                template = PromptTemplateFactory.create_template("analyze_image")
                metadata = {
                    "analysis_type": arguments.get("analysis_type", "general")
                }
                return template.generate_prompt(extracted_text, metadata)
            
            elif name == "extractInformation":
                if "information_type" not in arguments:
                    raise ValueError("Missing required argument 'information_type'")
                
                template = PromptTemplateFactory.create_template("extract_information")
                metadata = {
                    "information_type": arguments["information_type"]
                }
                return template.generate_prompt(extracted_text, metadata)
            
            elif name == "summarizeImageText":
                template = PromptTemplateFactory.create_template("summarize_text")
                metadata = {
                    "length": arguments.get("length", "short")
                }
                return template.generate_prompt(extracted_text, metadata)
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    def _register_resources(self):
        """Register MCP resources."""
        
        @self.server.list_resources()
        async def list_resources() -> list[types.Resource]:
            """List available resources."""
            return self.resource_manager.list_resources()
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> Union[types.TextResourceContents, types.BlobResourceContents]:
            """Read a resource."""
            # Extract resource ID from URI (format: mcp:///resource/{resource_id})
            if not uri.startswith("mcp:///resource/"):
                raise ValueError(f"Invalid resource URI format: {uri}")
            
            # Extract the resource ID from the URI
            resource_id = uri.split("mcp:///resource/")[1]
            
            try:
                return self.resource_manager.get_resource_content(resource_id)
            except Exception as e:
                raise ValueError(f"Failed to read resource: {str(e)}")
    
    async def run(self, transport: str = "stdio", port: int = 8000):
        """Run the server."""
        if transport == "stdio":
            from mcp.server.stdio import stdio_server
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.name,
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        )
                    )
                )
        elif transport == "sse":
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route
            
            sse = SseServerTransport("/messages")
            
            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await self.server.run(
                        streams[0],
                        streams[1],
                        InitializationOptions(
                            server_name=self.name,
                            server_version="0.1.0",
                            capabilities=self.server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={},
                            )
                        )
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
            # Use Config and Server classes to properly handle async
            config = uvicorn.Config(
                starlette_app, 
                host="0.0.0.0", 
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
        else:
            raise ValueError(f"Unsupported transport: {transport}")


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    """Main entry point for the image-ocr server."""
    server = ImageOcrServer("image-ocr-server")
    
    if transport == "stdio":
        anyio.run(lambda: server.run(transport))
    else:
        # Fix for SSE transport - properly await the coroutine
        async def run_sse_server():
            await server.run(transport, port)
            
        asyncio.run(run_sse_server())
    
    return 0


if __name__ == "__main__":
    main() 