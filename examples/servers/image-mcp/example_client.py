#!/usr/bin/env python3
"""
Example MCP client for the image-ocr server.
This script demonstrates how to connect to the server and use its capabilities.

Usage:
    python example_client.py                      # Uses default image URL
    python example_client.py --url IMAGE_URL      # Uses provided image URL
    python example_client.py --file IMAGE_PATH    # Uses local image file
"""

import asyncio
import sys
import argparse
import os
from typing import List, Optional
import mcp.types as types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

# Default image URL if no arguments provided
DEFAULT_IMAGE_URL = "https://www.gutenberg.org/cache/epub/1/pg1.cover.medium.jpg"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Example MCP client for image OCR server"
    )
    
    # Create a mutually exclusive group for image source
    source_group = parser.add_mutually_exclusive_group()
    
    source_group.add_argument(
        "--file", "-f",
        help="Path to a local image file (supported formats: jpg, jpeg, png)"
    )
    
    source_group.add_argument(
        "--url", "-u",
        help=f"URL of an image to download (default: {DEFAULT_IMAGE_URL})"
    )
    
    return parser.parse_args()

def print_help_message():
    """Print additional help information about the client."""
    print("\n" + "="*80)
    print("IMAGE OCR MCP CLIENT HELP")
    print("="*80)
    print("\nThis client demonstrates how to use the Image OCR MCP server.")
    print("\nSupported image formats:")
    print("  - JPEG/JPG: Joint Photographic Experts Group format")
    print("  - PNG: Portable Network Graphics format")
    print("\nCommand line options:")
    print("  python example_client.py                         # Use default image URL")
    print("  python example_client.py --url [URL]             # Use custom image URL")
    print("  python example_client.py --file [PATH]           # Use local image file")
    print("  python example_client.py --help                  # Show help message")
    print("\nExample with local file:")
    print("  python example_client.py --file /path/to/image.jpg")
    print("\nExample with URL:")
    print("  python example_client.py --url https://example.com/image.png")
    print("\nAvailable prompts:")
    print("  - analyzeImageContent: Analyzes the content of an image based on extracted text")
    print("      Arguments: resource_id (required), analysis_type (optional)")
    print("  - extractInformation: Extracts specific information from image text")
    print("      Arguments: resource_id (required), information_type (required)")
    print("  - summarizeImageText: Summarizes the text extracted from an image")
    print("      Arguments: resource_id (required), length (optional)")
    print("\nNote: If text extraction fails, try using an image with clear, readable text.")
    print("="*80)

async def run(args):
    """Run the example client with provided arguments."""
    
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="/Users/sughoshdivanji/.pyenv/shims/python",
        args=["-m", "mcp_image_ocr"],
        env={"PYTHONUNBUFFERED": "1"},  # Ensure Python output is unbuffered
        redirect_stderr=True  # Capture stderr for debugging
    )
    
    print("Connecting to image-ocr server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            result = await session.initialize()
            print("Connection established.")
            
            # List server capabilities
            print("\nServer capabilities:")
            capabilities = result.capabilities
            for capability_name, capability in {
                "prompts": capabilities.prompts,
                "resources": capabilities.resources,
                "tools": capabilities.tools,
                "logging": capabilities.logging,
            }.items():
                if capability:
                    print(f"- {capability_name}: {capability}")
            
            # Step 1: Process image (either from URL or local file)
            resource_id = None
            
            try:
                if args.file:
                    # Check if the file exists
                    if not os.path.exists(args.file):
                        print(f"\nError: File '{args.file}' does not exist.")
                        print_help_message()
                        return
                    
                    # Load image from local file
                    print(f"\n1. Loading image from file: {args.file}")
                    result = await session.call_tool("loadImageFromPath", {"path": args.file})
                else:
                    # Download image from URL
                    image_url = args.url or DEFAULT_IMAGE_URL
                    print(f"\n1. Downloading image from URL: {image_url}")
                    result = await session.call_tool("downloadImageFromUrl", {"url": image_url})
                
                # Extract resource ID from the result if successful
                if (result.content and 
                    hasattr(result.content[0], 'text') and 
                    "Resource ID:" in result.content[0].text):
                    print(result.content[0].text)
                    resource_id = result.content[0].text.split("Resource ID: ")[1]
                else:
                    print("Failed to process image: Unexpected response format")
                    if result.content and hasattr(result.content[0], 'text'):
                        print(result.content[0].text)
                    else:
                        print("No readable response received")
            except McpError as e:
                print(f"Failed to process image: {str(e)}")
                # Continue execution to show capabilities
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                print_help_message()
                return
            
            # Exit if we don't have a valid resource ID
            if not resource_id:
                print("\nExiting because no valid resource ID was obtained.")
                print_help_message()
                return
            
            # Step 2: Extract text from the image
            text_extraction_success = False
            print("\n2. Extracting text from the image...")
            try:
                result = await session.call_tool("extractTextFromImage", {"resource_id": resource_id})
                if result.content and hasattr(result.content[0], 'text'):
                    print(result.content[0].text)
                    text_extraction_success = "Text extracted successfully" in result.content[0].text
                else:
                    print("Failed to extract text: Unexpected response format")
            except Exception as e:
                print(f"Error during text extraction: {str(e)}")
                text_extraction_success = False
            
            # Step 3: List available prompts
            print("\n3. Available prompts:")
            try:
                prompts_result = await session.list_prompts()
                for prompt in prompts_result.prompts:
                    print(f"- {prompt.name}: {prompt.description}")
                    print(f"  Arguments: {[arg.name for arg in prompt.arguments or []]}")
            except Exception as e:
                print(f"Error listing prompts: {str(e)}")
            
            # Step 4: Use prompts only if text extraction succeeded
            if text_extraction_success:
                try:
                    # Step 4: Use a prompt with the extracted text
                    print("\n4. Using analyzeImageContent prompt:")
                    prompt_result = await session.get_prompt("analyzeImageContent", {"resource_id": resource_id})
                    
                    # Display the generated prompt
                    print("\nGenerated prompt:")
                    for message in prompt_result.messages:
                        print(f"{message.role}: {message.content.text}")
                    
                    # Step 4b: Use the extractInformation prompt
                    print("\n4b. Using extractInformation prompt (for dates):")
                    extract_result = await session.get_prompt("extractInformation", {
                        "resource_id": resource_id,
                        "information_type": "dates"
                    })
                    
                    # Display the generated prompt
                    print("\nGenerated prompt:")
                    for message in extract_result.messages:
                        print(f"{message.role}: {message.content.text}")
                    
                    # Step 4c: Use the summarizeImageText prompt
                    print("\n4c. Using summarizeImageText prompt:")
                    summary_result = await session.get_prompt("summarizeImageText", {
                        "resource_id": resource_id,
                        "length": "short"
                    })
                    
                    # Display the generated prompt
                    print("\nGenerated prompt:")
                    for message in summary_result.messages:
                        print(f"{message.role}: {message.content.text}")
                    
                    # Step 5: Use extracted text as context
                    print("\n5. Using extracted text as context:")
                    result = await session.call_tool("useTextAsContext", {"resource_id": resource_id})
                    
                    context_found = False
                    for content in result.content:
                        if hasattr(content, 'type') and content.type == "resource":
                            if hasattr(content.resource, 'text'):
                                print(f"Text successfully added as context: {len(content.resource.text)} characters")
                                context_found = True
                    
                    if not context_found:
                        print("Failed to add text as context: Response did not contain the expected data")
                except Exception as e:
                    print(f"Error working with extracted text: {str(e)}")
            else:
                print("\nSkipping prompt usage since text extraction failed.")
            
            # Step 6: List resources
            print("\n6. Available resources:")
            try:
                resources_result = await session.list_resources()
                if resources_result.resources:
                    for resource in resources_result.resources:
                        print(f"- {resource.name}: {resource.mimeType} - {resource.description}")
                else:
                    print("No resources available")
            except Exception as e:
                print(f"Error listing resources: {str(e)}")
            
            # Step 7: Print summary of how to use prompts in your own applications
            print("\n7. Using prompts in your own applications:")
            print("\nTo use these prompts in your own MCP client application:")
            print("  1. Connect to the server and initialize the session")
            print("  2. Load an image (either from URL or file) to get a resource ID")
            print("  3. Extract text from the image using the resource ID")
            print("  4. Use one of the available prompts with the resource ID:")
            print("     - session.get_prompt(\"analyzeImageContent\", {\"resource_id\": resource_id})")
            print("     - session.get_prompt(\"extractInformation\", {\"resource_id\": resource_id, \"information_type\": \"dates\"})")
            print("     - session.get_prompt(\"summarizeImageText\", {\"resource_id\": resource_id, \"length\": \"short\"})")
            print("  5. Use the returned prompt messages with your LLM")
            print("  6. Optionally use extracted text as context with the useTextAsContext tool")
            
            # Print help message at the end
            print_help_message()


if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(run(args)) 
