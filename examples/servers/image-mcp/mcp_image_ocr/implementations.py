"""Concrete implementations for the image-mcp server interfaces."""

import os
import io
import httpx
import mimetypes
from datetime import datetime
from PIL import Image
import pytesseract
from mcp_image_ocr.interfaces import ImageSource, TextExtractor, PromptTemplate
import mcp.types as types
import logging

# Set up logging
logging.basicConfig(
    filename='ocr_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Image validation constants
SUPPORTED_FORMATS = ["image/jpeg", "image/jpg", "image/png"]
MAX_IMAGE_SIZE = int(os.environ.get("IMAGE_MCP_MAX_IMAGE_SIZE", 10 * 1024 * 1024))  # 10MB default

class WebImageSource(ImageSource):
    """Image source for web URLs."""
    
    def __init__(self, url: str):
        self.url = url
        self.data = None
        self.content_type = None
        self._metadata = None
    
    async def download(self) -> bytes:
        """Download image from URL."""
        if self.data:
            return self.data
        
        headers = {
            "User-Agent": "MCP Image OCR Server (github.com/modelcontextprotocol/python-sdk)"
        }
        
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            response = await client.get(self.url)
            response.raise_for_status()
            
            self.content_type = response.headers.get("content-type", "")
            if self.content_type not in SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported image format: {self.content_type}")
            
            self.data = response.content
            if len(self.data) > MAX_IMAGE_SIZE:
                raise ValueError(f"Image too large: {len(self.data)} bytes")
            
            self._metadata = {
                "uri": self.url,
                "content_type": self.content_type,
                "size": len(self.data),
                "download_time": datetime.now().isoformat(),
            }
            
            return self.data
    
    def get_metadata(self) -> dict:
        """Get metadata about the image."""
        if not self._metadata:
            raise ValueError("Image not yet downloaded")
        return self._metadata


class LocalImageSource(ImageSource):
    """Image source for local files."""
    
    def __init__(self, path: str):
        self.path = path
        self.data = None
        self._metadata = None
    
    async def download(self) -> bytes:
        """Read image from local file."""
        if self.data:
            return self.data
        
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Image file not found: {self.path}")
        
        content_type, _ = mimetypes.guess_type(self.path)
        if content_type not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {content_type}")
        
        with open(self.path, "rb") as file:
            self.data = file.read()
        
        if len(self.data) > MAX_IMAGE_SIZE:
            raise ValueError(f"Image too large: {len(self.data)} bytes")
        
        self._metadata = {
            "uri": f"file://{self.path}",
            "content_type": content_type,
            "size": len(self.data),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(self.path)).isoformat(),
        }
        
        return self.data
    
    def get_metadata(self) -> dict:
        """Get metadata about the image."""
        if not self._metadata:
            raise ValueError("Image not yet read")
        return self._metadata


class TesseractTextExtractor(TextExtractor):
    """Text extractor using Tesseract OCR."""
    
    def __init__(self):
        self.last_confidence = 0.0
        self.last_text = ""
        # Use the full path to tesseract on this system
        self.tesseract_cmd = "/opt/homebrew/bin/tesseract"
        # Configure pytesseract to use the specified path
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        logging.debug(f"Setting pytesseract command to: {self.tesseract_cmd}")
    
    async def extract_text(self, image_data: bytes) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Log image details for debugging
            logging.debug(f"Image format: {image.format}, mode: {image.mode}, size: {image.size}")
            
            # Convert image to RGB mode if it's not already
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save image to a temporary file to avoid encoding issues with direct processing
            temp_image_path = "temp_ocr_image.png"
            image.save(temp_image_path)
            logging.debug(f"Saved image to temporary file: {temp_image_path}")
            
            # Try direct string extraction first
            try:
                extracted_text = pytesseract.image_to_string(temp_image_path)
                logging.debug(f"Direct extraction result: {extracted_text[:100]}...")
                
                if extracted_text and extracted_text.strip():
                    # Try to get confidence values
                    try:
                        data = pytesseract.image_to_data(temp_image_path, output_type=pytesseract.Output.DICT)
                        if len(data["conf"]) > 0:
                            conf_values = [float(c) for c in data["conf"] if float(c) >= 0]
                            if conf_values:
                                self.last_confidence = sum(conf_values) / len(conf_values)
                                logging.debug(f"Calculated confidence: {self.last_confidence:.2f}%")
                            else:
                                self.last_confidence = 50.0  # Default confidence
                                logging.debug("No valid confidence values, using default 50.0%")
                    except Exception as e:
                        logging.error(f"Error getting confidence values: {str(e)}")
                        self.last_confidence = 50.0  # Default confidence when we have text
                    
                    self.last_text = extracted_text
                    return self.last_text
            except Exception as e:
                logging.error(f"Error with direct extraction: {str(e)}")
            
            # If direct extraction failed, try with different PSM modes
            psm_modes = [6, 3, 4, 11]
            for psm_mode in psm_modes:
                try:
                    logging.debug(f"Trying PSM mode {psm_mode}")
                    config = f'--psm {psm_mode} -l eng'
                    
                    # Use the temp file to avoid encoding issues
                    extracted_text = pytesseract.image_to_string(temp_image_path, config=config)
                    
                    if extracted_text and extracted_text.strip():
                        logging.debug(f"Extracted text with PSM {psm_mode}: {extracted_text[:100]}...")
                        self.last_text = extracted_text
                        self.last_confidence = 50.0  # Default confidence when we have text with PSM
                        return self.last_text
                except Exception as e:
                    logging.error(f"Error with PSM {psm_mode}: {str(e)}")
                    continue
            
            # If we're here, all attempts failed
            logging.warning("No readable text found in the image")
            self.last_text = "No readable text found in the image."
            self.last_confidence = 0.0
            
            # Clean up temporary file
            try:
                os.remove(temp_image_path)
                logging.debug("Removed temporary image file")
            except Exception as e:
                logging.error(f"Error removing temp file: {str(e)}")
            
            return self.last_text
        
        except Exception as e:
            logging.error(f"General exception in extract_text: {str(e)}")
            self.last_confidence = 0.0
            self.last_text = f"Error extracting text: {str(e)}"
            return self.last_text
    
    def get_confidence_score(self) -> float:
        """Get confidence score of last extraction."""
        return self.last_confidence


class AzureTextExtractor(TextExtractor):
    """Text extractor using Azure Computer Vision."""
    
    def __init__(self):
        self.last_confidence = 0.0
        self.last_text = ""
        # Azure credentials should be read from environment variables
        self.api_key = os.environ.get("AZURE_VISION_API_KEY")
        self.endpoint = os.environ.get("AZURE_VISION_ENDPOINT")
    
    async def extract_text(self, image_data: bytes) -> str:
        """Extract text from image using Azure Computer Vision."""
        if not self.api_key or not self.endpoint:
            raise ValueError("Azure credentials not configured")
        
        # This is a placeholder implementation
        # In a real implementation, we would call Azure's Computer Vision API
        self.last_text = "Azure OCR implementation placeholder"
        self.last_confidence = 0.9
        return self.last_text
    
    def get_confidence_score(self) -> float:
        """Get confidence score of last extraction."""
        return self.last_confidence


class AnalyzeImagePrompt(PromptTemplate):
    """Prompt template for analyzing image content."""
    
    def generate_prompt(self, extracted_text: str, metadata: dict) -> types.GetPromptResult:
        """Generate a prompt for analyzing image content."""
        return types.GetPromptResult(
            description="Analyze the content of an image based on extracted text",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"I have an image with the following extracted text. "
                            f"Please analyze and explain what this image might contain or represent:\n\n"
                            f"{extracted_text}"
                        )
                    )
                )
            ]
        )


class ExtractInformationPrompt(PromptTemplate):
    """Prompt template for extracting specific information from image text."""
    
    def generate_prompt(self, extracted_text: str, metadata: dict) -> types.GetPromptResult:
        """Generate a prompt for extracting specific information."""
        info_type = metadata.get("information_type", "general")
        
        return types.GetPromptResult(
            description=f"Extract {info_type} information from image text",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"I have an image with the following extracted text. "
                            f"Please extract {info_type} information from it:\n\n"
                            f"{extracted_text}"
                        )
                    )
                )
            ]
        )


class SummarizeImageTextPrompt(PromptTemplate):
    """Prompt template for summarizing text extracted from an image."""
    
    def generate_prompt(self, extracted_text: str, metadata: dict) -> types.GetPromptResult:
        """Generate a prompt for summarizing image text."""
        length = metadata.get("length", "short")
        
        return types.GetPromptResult(
            description=f"Summarize the text extracted from an image",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"I have an image with the following extracted text. "
                            f"Please provide a {length} summary of it:\n\n"
                            f"{extracted_text}"
                        )
                    )
                )
            ]
        ) 