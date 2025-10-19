"""
PDF text extraction service using PyMuPDF (fitz).
Handles both text-based PDFs and image-based PDFs (with OCR fallback).
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from app.services.ocr import ocr_service

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Service for extracting text from PDF documents."""

    def __init__(self, use_ocr_fallback: bool = True):
        """
        Initialize PDF extractor.

        Args:
            use_ocr_fallback: If True, use OCR when text extraction yields little/no text
        """
        self.use_ocr_fallback = use_ocr_fallback

    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing:
            {
                "text": str,              # Full extracted text
                "pages": List[Dict],       # Per-page text and metadata
                "page_count": int,
                "metadata": Dict,          # PDF metadata
                "used_ocr": bool,          # Whether OCR was used
                "error": Optional[str]
            }

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If extraction fails
        """
        result = {
            "text": "",
            "pages": [],
            "page_count": 0,
            "metadata": {},
            "used_ocr": False,
            "error": None
        }

        try:
            # Check if file exists
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            logger.info(f"Extracting text from PDF: {pdf_path}")

            # Open PDF
            doc = fitz.open(pdf_path)
            result["page_count"] = len(doc)
            result["metadata"] = doc.metadata

            # Extract text from each page
            all_text = []
            pages_data = []

            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text()

                # If page has very little text, it might be scanned - try OCR
                if self.use_ocr_fallback and len(page_text.strip()) < 50:
                    logger.info(f"Page {page_num} has minimal text, attempting OCR")
                    try:
                        # Render page to image and OCR it
                        pix = page.get_pixmap(dpi=300)  # High DPI for better OCR
                        img_bytes = pix.tobytes("png")

                        ocr_result = ocr_service.extract_text_from_bytes(img_bytes)
                        if len(ocr_result["text"]) > len(page_text):
                            page_text = ocr_result["text"]
                            result["used_ocr"] = True
                            logger.info(f"OCR improved text extraction for page {page_num}")
                    except Exception as e:
                        logger.warning(f"OCR fallback failed for page {page_num}: {e}")

                # Store page data
                pages_data.append({
                    "page_number": page_num,
                    "text": page_text,
                    "char_count": len(page_text)
                })

                all_text.append(page_text)

            # Combine all text
            result["text"] = "\n\n".join(all_text)
            result["pages"] = pages_data

            doc.close()

            logger.info(f"Extracted {len(result['text'])} characters from {result['page_count']} pages")

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            result["error"] = str(e)
            raise

        return result

    def extract_page(self, pdf_path: str, page_number: int) -> Dict[str, Any]:
        """
        Extract text from a specific page of a PDF.

        Args:
            pdf_path: Path to the PDF file
            page_number: Page number (1-indexed)

        Returns:
            Dictionary with page text and metadata
        """
        try:
            doc = fitz.open(pdf_path)

            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Invalid page number: {page_number} (PDF has {len(doc)} pages)")

            page = doc[page_number - 1]  # fitz uses 0-indexed pages
            page_text = page.get_text()

            # OCR fallback if needed
            if self.use_ocr_fallback and len(page_text.strip()) < 50:
                try:
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    ocr_result = ocr_service.extract_text_from_bytes(img_bytes)
                    if len(ocr_result["text"]) > len(page_text):
                        page_text = ocr_result["text"]
                except Exception as e:
                    logger.warning(f"OCR fallback failed: {e}")

            doc.close()

            return {
                "page_number": page_number,
                "text": page_text,
                "char_count": len(page_text)
            }

        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            raise

    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get PDF metadata without extracting text.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "is_encrypted": doc.is_encrypted,
                "is_pdf": doc.is_pdf
            }
            doc.close()
            return info
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            raise


# Global instance
pdf_extractor = PDFExtractor(use_ocr_fallback=True)
