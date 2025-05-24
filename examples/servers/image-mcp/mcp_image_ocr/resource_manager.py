"""Resource manager for the image-mcp server."""

import os
import uuid
import json
import base64
from typing import Dict, List, Optional, Union
from datetime import datetime
import mcp.types as types
from mcp_image_ocr.factories import ImageSourceFactory, TextExtractorFactory

class ResourceManager:
    """Manages image resources and their metadata."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the resource manager."""
        self.cache_dir = cache_dir or os.environ.get("IMAGE_MCP_CACHE_DIR") or "./.image_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Resource metadata storage
        self.resources: Dict[str, Dict] = {}
    
    async def add_image_from_url(self, url: str) -> str:
        """Add an image from a URL."""
        image_source = ImageSourceFactory.create_image_source(url)
        image_data = await image_source.download()
        metadata = image_source.get_metadata()
        
        # Generate a resource ID
        resource_id = f"image-{uuid.uuid4()}"
        
        # Save image to cache
        cache_path = os.path.join(self.cache_dir, f"{resource_id}.data")
        with open(cache_path, "wb") as f:
            f.write(image_data)
        
        # Save metadata
        self.resources[resource_id] = {
            "id": resource_id,
            "type": metadata["content_type"],
            "uri": metadata["uri"],
            "size": metadata["size"],
            "created_at": datetime.now().isoformat(),
            "cache_path": cache_path,
            "text_extracted": False,
            "extracted_text": None,
            "confidence_score": None,
        }
        
        return resource_id
    
    async def add_image_from_path(self, path: str) -> str:
        """Add an image from a local file path."""
        image_source = ImageSourceFactory.create_image_source(path)
        image_data = await image_source.download()
        metadata = image_source.get_metadata()
        
        # Generate a resource ID
        resource_id = f"image-{uuid.uuid4()}"
        
        # Save image to cache
        cache_path = os.path.join(self.cache_dir, f"{resource_id}.data")
        with open(cache_path, "wb") as f:
            f.write(image_data)
        
        # Save metadata
        self.resources[resource_id] = {
            "id": resource_id,
            "type": metadata["content_type"],
            "uri": metadata["uri"],
            "size": metadata["size"],
            "created_at": datetime.now().isoformat(),
            "cache_path": cache_path,
            "text_extracted": False,
            "extracted_text": None,
            "confidence_score": None,
        }
        
        return resource_id
    
    async def extract_text_from_image(self, resource_id: str, extractor_type: str = "tesseract") -> dict:
        """Extract text from an image."""
        if resource_id not in self.resources:
            raise ValueError(f"Resource not found: {resource_id}")
        
        resource = self.resources[resource_id]
        
        # Load image data from cache
        with open(resource["cache_path"], "rb") as f:
            image_data = f.read()
        
        # Extract text
        extractor = TextExtractorFactory.create_extractor(extractor_type)
        try:
            extracted_text = await extractor.extract_text(image_data)
            confidence_score = extractor.get_confidence_score()
            
            # Update resource metadata
            resource["text_extracted"] = True
            resource["extracted_text"] = extracted_text
            resource["confidence_score"] = confidence_score
            resource["text_extraction_time"] = datetime.now().isoformat()
            resource["text_extractor"] = extractor_type
            
            result = {
                "resource_id": resource_id,
                "text": extracted_text,
                "confidence": confidence_score
            }
            
            return result
        except Exception as e:
            # Still update the resource with the error message
            error_message = f"Text extraction failed: {str(e)}"
            resource["text_extracted"] = True
            resource["extracted_text"] = error_message
            resource["confidence_score"] = 0.0
            resource["text_extraction_time"] = datetime.now().isoformat()
            resource["text_extractor"] = extractor_type
            
            raise ValueError(f"Failed to extract text: {str(e)}")
    
    def get_resource(self, resource_id: str) -> dict:
        """Get a resource by ID."""
        if resource_id not in self.resources:
            raise ValueError(f"Resource not found: {resource_id}")
        
        return self.resources[resource_id]
    
    def list_resources(self) -> List[types.Resource]:
        """List all resources."""
        return [
            types.Resource(
                uri=f"mcp:///resource/{resource_id}",
                name=resource_id,
                description=f"{'Image' if not resource['text_extracted'] else 'Extracted Text'} - {resource['uri']}",
                mimeType=resource["type"] if not resource["text_extracted"] else "text/plain",
            )
            for i, (resource_id, resource) in enumerate(self.resources.items())
        ]
    
    def get_resource_content(self, resource_id: str) -> Union[types.TextResourceContents, types.BlobResourceContents]:
        """Get resource content."""
        if resource_id not in self.resources:
            raise ValueError(f"Resource not found: {resource_id}")
        
        resource = self.resources[resource_id]
        
        # Create a valid URI from the resource ID
        uri = f"mcp:///resource/{resource_id}"
        
        if resource["text_extracted"] and resource["extracted_text"]:
            # Return extracted text
            return types.TextResourceContents(
                uri=uri,
                mimeType="text/plain",
                text=resource["extracted_text"]
            )
        else:
            # Return image data
            with open(resource["cache_path"], "rb") as f:
                image_data = f.read()
            
            # Convert binary data to base64
            encoded_data = base64.b64encode(image_data).decode('utf-8')
            
            return types.BlobResourceContents(
                uri=uri,
                mimeType=resource["type"],
                blob=encoded_data
            )
    
    def get_extracted_text(self, resource_id: str) -> Optional[str]:
        """Get extracted text from a resource."""
        if resource_id not in self.resources:
            raise ValueError(f"Resource not found: {resource_id}")
        
        resource = self.resources[resource_id]
        
        if not resource["text_extracted"] or not resource["extracted_text"]:
            return None
        
        return resource["extracted_text"] 