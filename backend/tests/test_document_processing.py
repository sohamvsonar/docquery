"""
Unit tests for document processing services.
Tests OCR, PDF extraction, chunking, and the document processor.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.chunker import TextChunker
from app.services.document_processor import DocumentProcessor


class TestTextChunker:
    """Test text chunking functionality."""

    def test_chunk_simple_text(self):
        """Test chunking a simple text."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)

        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = chunker.chunk_text(text)

        assert len(chunks) > 0
        assert all('content' in chunk for chunk in chunks)
        assert all('chunk_index' in chunk for chunk in chunks)
        assert all('token_count' in chunk for chunk in chunks)

    def test_chunk_index_sequential(self):
        """Test that chunk indices are sequential."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=5)

        text = " ".join([f"Sentence number {i}." for i in range(50)])
        chunks = chunker.chunk_text(text)

        indices = [chunk['chunk_index'] for chunk in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_with_metadata(self):
        """Test chunking with metadata."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        text = "Test content"
        metadata = {"page_number": 5, "document_id": 123}
        chunks = chunker.chunk_text(text, metadata=metadata)

        assert len(chunks) > 0
        assert chunks[0]['page_number'] == 5
        assert chunks[0]['document_id'] == 123

    def test_empty_text(self):
        """Test chunking empty text."""
        chunker = TextChunker()

        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

        chunks = chunker.chunk_text("   ")
        assert len(chunks) == 0

    def test_token_counting(self):
        """Test token counting."""
        chunker = TextChunker()

        text = "Hello world"
        token_count = chunker.count_tokens(text)

        assert token_count > 0
        assert isinstance(token_count, int)

    def test_chunk_by_pages(self):
        """Test chunking with page data."""
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)

        pages_data = [
            {"text": "Page one content. This is the first page.", "page_number": 1},
            {"text": "Page two content. This is the second page.", "page_number": 2}
        ]

        chunks = chunker.chunk_by_pages(pages_data)

        assert len(chunks) > 0
        # Should have chunks from both pages
        page_numbers = [chunk.get('page_number') for chunk in chunks]
        assert 1 in page_numbers
        assert 2 in page_numbers


class TestDocumentProcessor:
    """Test document processor."""

    @patch('app.services.document_processor.pdf_extractor')
    def test_process_pdf(self, mock_pdf):
        """Test PDF processing."""
        mock_pdf.extract_text.return_value = {
            "text": "Extracted PDF text",
            "page_count": 2,
            "metadata": {},
            "used_ocr": False,
            "pages": [
                {"page_number": 1, "text": "Page 1", "char_count": 6},
                {"page_number": 2, "text": "Page 2", "char_count": 6}
            ],
            "error": None
        }

        processor = DocumentProcessor()
        result = processor.process_document("test.pdf", mime_type="application/pdf")

        assert result["success"] is True
        assert "Extracted PDF text" in result["text"]
        assert len(result["chunks"]) > 0
        mock_pdf.extract_text.assert_called_once()

    @patch('app.services.document_processor.ocr_service')
    def test_process_image(self, mock_ocr):
        """Test image processing with OCR."""
        mock_ocr.extract_text.return_value = {
            "text": "OCR extracted text",
            "confidence": 95.5,
            "language": "eng",
            "error": None
        }

        processor = DocumentProcessor()
        result = processor.process_document("test.png", mime_type="image/png")

        assert result["success"] is True
        assert result["text"] == "OCR extracted text"
        assert len(result["chunks"]) > 0
        mock_ocr.extract_text.assert_called_once()

    @patch('app.services.document_processor.audio_transcription_service')
    def test_process_audio(self, mock_audio):
        """Test audio transcription."""
        mock_audio.transcribe.return_value = {
            "text": "Transcribed audio text",
            "language": "en",
            "duration": 120.5,
            "error": None
        }

        processor = DocumentProcessor()
        result = processor.process_document("test.mp3", mime_type="audio/mpeg")

        assert result["success"] is True
        assert result["text"] == "Transcribed audio text"
        assert len(result["chunks"]) > 0
        mock_audio.transcribe.assert_called_once()

    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        processor = DocumentProcessor()
        result = processor.process_document("test.xyz", mime_type="application/unknown")

        assert result["success"] is False
        assert result["error"] is not None
        assert "Unsupported" in result["error"]

    @patch('app.services.document_processor.pdf_extractor')
    def test_extraction_error_handling(self, mock_pdf):
        """Test error handling during extraction."""
        mock_pdf.extract_text.side_effect = Exception("Extraction failed")

        processor = DocumentProcessor()
        result = processor.process_document("test.pdf", mime_type="application/pdf")

        assert result["success"] is False
        assert result["error"] is not None

    def test_mime_type_detection(self):
        """Test MIME type detection."""
        processor = DocumentProcessor()

        # Test detection from extension
        mime_type = processor._detect_mime_type("document.pdf")
        assert "pdf" in mime_type.lower()

        mime_type = processor._detect_mime_type("image.png")
        assert "png" in mime_type.lower()

        mime_type = processor._detect_mime_type("audio.mp3")
        assert "audio" in mime_type.lower() or "mpeg" in mime_type.lower()
