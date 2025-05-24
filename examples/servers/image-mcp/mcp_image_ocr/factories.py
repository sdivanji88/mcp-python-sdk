"""Factory implementations for the image-mcp server."""

import os
from mcp_image_ocr.interfaces import ImageSource, TextExtractor, PromptTemplate
from mcp_image_ocr.implementations import (
    WebImageSource, LocalImageSource,
    TesseractTextExtractor, AzureTextExtractor,
    AnalyzeImagePrompt, ExtractInformationPrompt, SummarizeImageTextPrompt
)

class ImageSourceFactory:
    """Factory for creating image sources."""
    
    @staticmethod
    def create_image_source(uri: str) -> ImageSource:
        """Create an image source based on the URI."""
        if uri.startswith(("http://", "https://")):
            return WebImageSource(uri)
        elif uri.startswith("file://") or os.path.exists(uri):
            # Strip file:// prefix if present
            path = uri[7:] if uri.startswith("file://") else uri
            return LocalImageSource(path)
        else:
            raise ValueError(f"Unsupported image source: {uri}")


class TextExtractorFactory:
    """Factory for creating text extractors."""
    
    @staticmethod
    def create_extractor(extractor_type: str = "tesseract") -> TextExtractor:
        """Create a text extractor based on the type."""
        if extractor_type == "tesseract":
            return TesseractTextExtractor()
        elif extractor_type == "azure":
            return AzureTextExtractor()
        # Add more extractors as needed
        else:
            raise ValueError(f"Unsupported text extractor: {extractor_type}")


class PromptTemplateFactory:
    """Factory for creating prompt templates."""
    
    @staticmethod
    def create_template(template_type: str) -> PromptTemplate:
        """Create a prompt template based on the type."""
        if template_type == "analyze_image":
            return AnalyzeImagePrompt()
        elif template_type == "extract_information":
            return ExtractInformationPrompt()
        elif template_type == "summarize_text":
            return SummarizeImageTextPrompt()
        # Add more templates as needed
        else:
            raise ValueError(f"Unsupported prompt template: {template_type}") 