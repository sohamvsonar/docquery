"""
OCR service using Tesseract for extracting text from images.
Supports various image formats (PNG, JPG, TIFF, etc.).
"""

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

from PIL import Image
from typing import Optional, Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images using Tesseract OCR."""

    def __init__(self, language: str = "eng"):
        """
        Initialize OCR service.

        Args:
            language: Tesseract language code (default: "eng" for English)
        """
        self.language = language
        self.enabled = TESSERACT_AVAILABLE

        if not self.enabled:
            logger.warning(
                "Tesseract is not available. Image OCR will be disabled. "
                "Install Tesseract OCR and pytesseract to enable image processing."
            )

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from an image file using OCR.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with extracted text, confidence, and metadata
            {
                "text": str,
                "confidence": float,
                "language": str,
                "page_count": int,
                "error": Optional[str]
            }

        Raises:
            FileNotFoundError: If image file doesn't exist
            Exception: If OCR processing fails
        """
        result = {
            "text": "",
            "confidence": 0.0,
            "language": self.language,
            "page_count": 1,
            "error": None
        }

        # Check if Tesseract is available
        if not self.enabled:
            error_msg = (
                "Tesseract OCR is not installed. "
                "Please install Tesseract OCR to process images. "
                "Instructions: https://github.com/tesseract-ocr/tesseract"
            )
            logger.error(error_msg)
            result["error"] = error_msg
            raise Exception(error_msg)

        try:
            # Check if file exists
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Open and process image
            logger.info(f"Processing image with OCR: {image_path}")
            image = Image.open(image_path)

            # Extract text
            text = pytesseract.image_to_string(image, lang=self.language)
            result["text"] = text.strip()

            # Get confidence score (OCR quality metric)
            # pytesseract returns confidence as dict per word
            try:
                data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                if confidences:
                    result["confidence"] = sum(confidences) / len(confidences)
                else:
                    result["confidence"] = 0.0
            except Exception as e:
                logger.warning(f"Could not calculate OCR confidence: {e}")
                result["confidence"] = 0.0

            logger.info(f"OCR extracted {len(result['text'])} characters with {result['confidence']:.2f}% confidence")

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"OCR processing failed for {image_path}: {e}")
            result["error"] = str(e)
            raise

        return result

    def extract_text_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from image bytes (useful for in-memory processing).

        Args:
            image_bytes: Image data as bytes

        Returns:
            Dictionary with extracted text and metadata
        """
        result = {
            "text": "",
            "confidence": 0.0,
            "language": self.language,
            "error": None
        }

        # Check if Tesseract is available
        if not self.enabled:
            error_msg = (
                "Tesseract OCR is not installed. "
                "Please install Tesseract OCR to process images. "
                "Instructions: https://github.com/tesseract-ocr/tesseract"
            )
            logger.error(error_msg)
            result["error"] = error_msg
            raise Exception(error_msg)

        try:
            from io import BytesIO
            image = Image.open(BytesIO(image_bytes))

            text = pytesseract.image_to_string(image, lang=self.language)
            result["text"] = text.strip()

            # Get confidence
            try:
                data = pytesseract.image_to_data(image, lang=self.language, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                if confidences:
                    result["confidence"] = sum(confidences) / len(confidences)
            except Exception:
                result["confidence"] = 0.0

        except Exception as e:
            logger.error(f"OCR processing from bytes failed: {e}")
            result["error"] = str(e)
            raise

        return result


# Global instance
ocr_service = OCRService()
