"""
Intelligent text chunking service for creating optimal document segments.
Implements token-aware chunking with sentence boundary preservation.
"""

import re
import logging
from typing import List, Dict, Any
import tiktoken
import nltk
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

# Download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception as e:
        logger.warning(f"Could not download NLTK data: {e}")


class TextChunker:
    """
    Intelligent text chunking with token-aware splitting and sentence preservation.

    Features:
    - Token-based chunking (respects model token limits)
    - Sentence boundary preservation (doesn't split mid-sentence)
    - Configurable chunk size and overlap
    - Metadata tracking (original position, page numbers)
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base",  # GPT-4 encoding
        min_chunk_size: int = 100
    ):
        """
        Initialize text chunker.

        Args:
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
            encoding_name: Tiktoken encoding name
            min_chunk_size: Minimum chunk size (reject chunks smaller than this)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(f"Could not load encoding {encoding_name}: {e}, using default")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk text intelligently with sentence boundary preservation.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk (e.g., page_number, document_id)

        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}

        # Split text into sentences
        try:
            sentences = sent_tokenize(text)
        except Exception as e:
            logger.warning(f"NLTK sentence tokenization failed: {e}, using simple split")
            # Fallback to simple sentence splitting
            sentences = re.split(r'[.!?]+\s+', text)

        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = self.count_tokens(sentence)

            # If a single sentence is longer than chunk_size, split it further
            if sentence_tokens > self.chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    if self.count_tokens(chunk_text) >= self.min_chunk_size:
                        chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))
                    current_chunk = []
                    current_token_count = 0

                # Split long sentence by tokens
                long_sentence_chunks = self._split_long_sentence(sentence)
                for sc in long_sentence_chunks:
                    if self.count_tokens(sc) >= self.min_chunk_size:
                        chunks.append(self._create_chunk(sc, len(chunks), metadata))
                continue

            # Check if adding this sentence exceeds chunk size
            if current_token_count + sentence_tokens > self.chunk_size:
                # Save current chunk
                chunk_text = " ".join(current_chunk)
                if self.count_tokens(chunk_text) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences + [sentence]
                current_token_count = self.count_tokens(" ".join(current_chunk))
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_token_count += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if self.count_tokens(chunk_text) >= self.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, len(chunks), metadata))

        logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")

        return chunks

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """
        Split a very long sentence by tokens.

        Args:
            sentence: Sentence to split

        Returns:
            List of sentence parts
        """
        tokens = self.encoding.encode(sentence)
        chunks = []

        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

        return chunks

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """
        Get sentences for overlap between chunks.

        Args:
            sentences: Current chunk sentences

        Returns:
            Sentences to include in overlap
        """
        overlap_sentences = []
        overlap_tokens = 0

        # Work backwards through sentences to create overlap
        for sentence in reversed(sentences):
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break

        return overlap_sentences

    def _create_chunk(
        self,
        text: str,
        index: int,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a chunk dictionary with metadata.

        Args:
            text: Chunk text
            index: Chunk index
            metadata: Additional metadata

        Returns:
            Chunk dictionary
        """
        return {
            "content": text,
            "chunk_index": index,
            "token_count": self.count_tokens(text),
            "char_count": len(text),
            **metadata
        }

    def chunk_by_pages(
        self,
        pages_data: List[Dict[str, Any]],
        page_text_key: str = "text",
        page_number_key: str = "page_number"
    ) -> List[Dict[str, Any]]:
        """
        Chunk text from multiple pages while preserving page metadata.

        Args:
            pages_data: List of page dictionaries with text and page numbers
            page_text_key: Key for text in page dict
            page_number_key: Key for page number in page dict

        Returns:
            List of chunks with page metadata
        """
        all_chunks = []

        for page_data in pages_data:
            page_text = page_data.get(page_text_key, "")
            page_number = page_data.get(page_number_key)

            if not page_text.strip():
                continue

            # Chunk this page's text
            page_chunks = self.chunk_text(
                page_text,
                metadata={"page_number": page_number}
            )

            all_chunks.extend(page_chunks)

        # Reindex chunks globally
        for i, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = i

        return all_chunks


# Global instance with sensible defaults
text_chunker = TextChunker(
    chunk_size=512,        # ~512 tokens per chunk
    chunk_overlap=50,      # ~50 token overlap
    min_chunk_size=100     # Minimum 100 tokens
)
