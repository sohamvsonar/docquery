"""
Document processor that orchestrates extraction, chunking, and storage.
Handles different document types (PDF, images, audio) and manages the processing pipeline.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import mimetypes

from app.services.ocr import ocr_service
from app.services.pdf_extractor import pdf_extractor
from app.services.audio_transcription import audio_transcription_service
from app.services.chunker import text_chunker
from app.services.docx_extractor import docx_extractor

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Orchestrates document processing pipeline:
    1. Detect document type
    2. Extract text (OCR/PDF/Audio)
    3. Chunk text intelligently
    4. Return processed data for storage
    """

    # Supported MIME types
    PDF_TYPES = ['application/pdf']
    IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'image/bmp', 'image/gif']
    AUDIO_TYPES = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/m4a', 'audio/ogg', 'audio/flac']
    DOCX_TYPES = [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
    TEXT_TYPES = [
        'text/plain',
        'text/markdown',
        'text/x-markdown',
        'text/html',
        'text/csv',
        'text/x-csv',
        'application/csv',
        'application/vnd.ms-excel',  # common CSV content-type from some browsers
        'application/json',
        'application/xml',
        'text/xml'
    ]

    def __init__(self):
        """Initialize document processor with all extraction services."""
        self.ocr = ocr_service
        self.pdf = pdf_extractor
        self.audio = audio_transcription_service
        self.docx = docx_extractor
        self.chunker = text_chunker

    def process_document(
        self,
        file_path: str,
        mime_type: str = None,
        chunk_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline.

        Args:
            file_path: Path to the document file
            mime_type: MIME type of the file (auto-detected if not provided)
            chunk_config: Optional chunking configuration

        Returns:
            Dictionary containing:
            {
                "success": bool,
                "text": str,              # Full extracted text
                "chunks": List[Dict],     # Chunked segments
                "metadata": Dict,         # Extraction metadata
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "text": "",
            "chunks": [],
            "metadata": {},
            "error": None
        }

        try:
            # Detect MIME type if not provided
            if not mime_type:
                mime_type = self._detect_mime_type(file_path)
                logger.info(f"Detected MIME type: {mime_type}")

            result["metadata"]["mime_type"] = mime_type

            # Route to appropriate extractor
            if mime_type in self.PDF_TYPES:
                extraction_result = self._process_pdf(file_path)
            elif mime_type in self.IMAGE_TYPES:
                extraction_result = self._process_image(file_path)
            elif mime_type in self.AUDIO_TYPES:
                extraction_result = self._process_audio(file_path)
            elif mime_type in self.DOCX_TYPES:
                extraction_result = self._process_docx(file_path)
            elif mime_type in self.TEXT_TYPES:
                extraction_result = self._process_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {mime_type}")

            # Check extraction success
            if extraction_result.get("error"):
                result["error"] = extraction_result["error"]
                return result

            # Get extracted text
            result["text"] = extraction_result.get("text", "")
            result["metadata"].update(extraction_result.get("metadata", {}))

            # Chunk the text
            if result["text"]:
                chunks = self._chunk_document(
                    result["text"],
                    extraction_result,
                    chunk_config
                )
                result["chunks"] = chunks
            else:
                logger.warning("No text extracted from document")

            result["success"] = True
            logger.info(
                f"Successfully processed document: "
                f"{len(result['text'])} chars, {len(result['chunks'])} chunks"
            )

        except Exception as e:
            logger.error(f"Document processing failed: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    def _detect_mime_type(self, file_path: str) -> str:
        """
        Detect MIME type of a file.

        Args:
            file_path: Path to file

        Returns:
            MIME type string
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Fallback: try to detect from extension
            ext = Path(file_path).suffix.lower()
            ext_to_mime = {
                '.pdf': 'application/pdf',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.tiff': 'image/tiff',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.m4a': 'audio/m4a',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.markdown': 'text/markdown',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.csv': 'text/csv',
                '.json': 'application/json',
                '.xml': 'text/xml'
            }
            mime_type = ext_to_mime.get(ext, 'application/octet-stream')

        return mime_type

    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF document."""
        logger.info(f"Processing PDF: {file_path}")

        try:
            pdf_result = self.pdf.extract_text(file_path)

            return {
                "text": pdf_result["text"],
                "metadata": {
                    "page_count": pdf_result["page_count"],
                    "pdf_metadata": pdf_result["metadata"],
                    "used_ocr": pdf_result["used_ocr"]
                },
                "pages": pdf_result["pages"],
                "error": pdf_result.get("error")
            }
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return {"text": "", "metadata": {}, "error": str(e)}

    def _process_image(self, file_path: str) -> Dict[str, Any]:
        """Process image document with OCR."""
        logger.info(f"Processing image: {file_path}")

        try:
            ocr_result = self.ocr.extract_text(file_path)

            return {
                "text": ocr_result["text"],
                "metadata": {
                    "ocr_confidence": ocr_result["confidence"],
                    "language": ocr_result["language"]
                },
                "error": ocr_result.get("error")
            }
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return {"text": "", "metadata": {}, "error": str(e)}

    def _process_audio(self, file_path: str) -> Dict[str, Any]:
        """Process audio file with transcription."""
        logger.info(f"Processing audio: {file_path}")

        try:
            audio_result = self.audio.transcribe(file_path)

            return {
                "text": audio_result["text"],
                "metadata": {
                    "language": audio_result["language"],
                    "duration": audio_result.get("duration")
                },
                "error": audio_result.get("error")
            }
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return {"text": "", "metadata": {}, "error": str(e)}

    def _process_docx(self, file_path: str) -> Dict[str, Any]:
        """Process DOCX/DOC document."""
        logger.info(f"Processing DOCX: {file_path}")

        try:
            docx_result = self.docx.extract_text(file_path)

            return {
                "text": docx_result["text"],
                "metadata": {
                    "paragraph_count": len(docx_result.get("paragraphs", [])),
                    "table_count": len(docx_result.get("tables", [])),
                    "document_properties": docx_result.get("metadata", {})
                },
                "paragraphs": docx_result.get("paragraphs", []),
                "error": docx_result.get("error")
            }
        except Exception as e:
            logger.error(f"DOCX processing failed: {e}")
            return {"text": "", "metadata": {}, "error": str(e)}

    def _process_text(self, file_path: str) -> Dict[str, Any]:
        """Process text-based files (TXT, MD, HTML, CSV, JSON, XML)."""
        logger.info(f"Processing text file: {file_path}")

        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            text = None
            used_encoding = None

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        text = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                raise ValueError("Could not decode file with any supported encoding")

            return {
                "text": text.strip(),
                "metadata": {
                    "encoding": used_encoding,
                    "char_count": len(text),
                    "line_count": text.count('\n') + 1
                },
                "error": None
            }
        except Exception as e:
            logger.error(f"Text file processing failed: {e}")
            return {"text": "", "metadata": {}, "error": str(e)}

    def _chunk_document(
        self,
        text: str,
        extraction_result: Dict[str, Any],
        chunk_config: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk document text intelligently.

        Args:
            text: Full document text
            extraction_result: Result from extraction (may contain page info)
            chunk_config: Optional chunking configuration

        Returns:
            List of chunk dictionaries
        """
        # Use page-aware chunking if pages are available
        if "pages" in extraction_result and extraction_result["pages"]:
            logger.info("Using page-aware chunking")
            chunks = self.chunker.chunk_by_pages(extraction_result["pages"])
        else:
            # Standard chunking
            logger.info("Using standard chunking")
            chunks = self.chunker.chunk_text(text)

        return chunks


# Global instance
document_processor = DocumentProcessor()
