"""Interface definitions for the image-mcp server."""

from abc import ABC, abstractmethod
import mcp.types as types

class ImageSource(ABC):
    """Interface for image sources."""
    
    @abstractmethod
    async def download(self) -> bytes:
        """Download the image and return its bytes"""
        pass
    
    @abstractmethod
    def get_metadata(self) -> dict:
        """Return metadata about the image"""
        pass


class TextExtractor(ABC):
    """Interface for text extractors."""
    
    @abstractmethod
    async def extract_text(self, image_data: bytes) -> str:
        """Extract text from image data"""
        pass
    
    @abstractmethod
    def get_confidence_score(self) -> float:
        """Return confidence score of last extraction"""
        pass


class PromptTemplate(ABC):
    """Interface for prompt templates."""
    
    @abstractmethod
    def generate_prompt(self, extracted_text: str, metadata: dict) -> types.GetPromptResult:
        """Generate a prompt with the extracted text"""
        pass 