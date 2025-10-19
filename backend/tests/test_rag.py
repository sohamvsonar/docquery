"""
Tests for RAG (Retrieval-Augmented Generation) functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.generator import RAGGenerator
from app.services.citation_tracker import CitationTracker


class TestRAGGenerator:
    """Tests for RAG generation service."""

    @patch('app.services.generator.OpenAI')
    def test_generate_answer_success(self, mock_openai):
        """Test successful answer generation."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Machine learning is a subset of AI [1]."))]
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Create generator
        generator = RAGGenerator()

        # Mock search results
        search_results = [
            {
                "chunk_id": 1,
                "document_id": 1,
                "document_filename": "ml_guide.pdf",
                "content": "Machine learning is a subset of artificial intelligence.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.9
            }
        ]

        # Generate answer
        result = generator.generate(
            query="What is machine learning?",
            search_results=search_results
        )

        assert "answer" in result
        assert "citations" in result
        assert "usage" in result
        assert result["usage"]["total_tokens"] == 150
        assert len(result["answer"]) > 0

    def test_generate_with_no_results(self):
        """Test generation when no search results available."""
        generator = RAGGenerator()

        result = generator.generate(
            query="What is machine learning?",
            search_results=[]
        )

        assert "don't have any relevant documents" in result["answer"].lower()
        assert len(result["citations"]) == 0

    def test_format_context(self):
        """Test context formatting from search results."""
        generator = RAGGenerator()

        search_results = [
            {
                "chunk_id": 1,
                "document_filename": "doc1.pdf",
                "content": "Machine learning is AI.",
                "page_number": 1,
                "chunk_index": 0
            },
            {
                "chunk_id": 2,
                "document_filename": "doc2.pdf",
                "content": "Neural networks are ML models.",
                "page_number": None,
                "chunk_index": 1
            }
        ]

        context = generator._format_context(search_results)

        assert "[1]" in context
        assert "[2]" in context
        assert "doc1.pdf" in context
        assert "doc2.pdf" in context
        assert "Machine learning is AI" in context
        assert "Page 1" in context

    def test_extract_citations(self):
        """Test citation extraction from answer."""
        generator = RAGGenerator()

        answer = "ML is a subset of AI [1]. Neural networks are ML models [2][3]."
        search_results = [
            {"chunk_id": 1, "document_filename": "doc1.pdf", "content": "Text 1", "chunk_index": 0},
            {"chunk_id": 2, "document_filename": "doc2.pdf", "content": "Text 2", "chunk_index": 1},
            {"chunk_id": 3, "document_filename": "doc3.pdf", "content": "Text 3", "chunk_index": 2}
        ]

        citations = generator._extract_citations(answer, search_results)

        assert len(citations) == 3
        assert citations[0]["citation_number"] == 1
        assert citations[1]["citation_number"] == 2
        assert citations[2]["citation_number"] == 3

    @patch('app.services.generator.OpenAI')
    def test_generate_stream(self, mock_openai):
        """Test streaming answer generation."""
        # Mock OpenAI streaming response
        mock_client = Mock()

        # Mock stream with chunks
        mock_chunks = [
            Mock(choices=[Mock(delta=Mock(content="Machine "))]),
            Mock(choices=[Mock(delta=Mock(content="learning "))]),
            Mock(choices=[Mock(delta=Mock(content="is AI."))]),
        ]

        mock_client.chat.completions.create.return_value = iter(mock_chunks)
        mock_openai.return_value = mock_client

        generator = RAGGenerator()

        search_results = [
            {
                "chunk_id": 1,
                "document_filename": "ml_guide.pdf",
                "content": "Machine learning is artificial intelligence.",
                "chunk_index": 0
            }
        ]

        # Collect streamed chunks
        chunks = list(generator.generate_stream(
            query="What is ML?",
            search_results=search_results
        ))

        assert len(chunks) > 0
        full_answer = "".join(chunks)
        assert len(full_answer) > 0


class TestCitationTracker:
    """Tests for citation tracking service."""

    def test_extract_citations(self):
        """Test citation number extraction."""
        tracker = CitationTracker()

        text = "This is a statement [1]. Another claim [2][3]. And more [1]."
        citations = tracker.extract_citations(text)

        assert citations == [1, 2, 3]

    def test_validate_citations_valid(self):
        """Test validation with valid citations."""
        tracker = CitationTracker()

        text = "Valid citations [1] and [2]."
        is_valid, errors = tracker.validate_citations(text, max_citation_number=5)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_citations_invalid(self):
        """Test validation with invalid citations."""
        tracker = CitationTracker()

        text = "Invalid citation [10] and [0]."
        is_valid, errors = tracker.validate_citations(text, max_citation_number=5)

        assert is_valid is False
        assert len(errors) > 0

    def test_map_citations_to_sources(self):
        """Test mapping citations to source documents."""
        tracker = CitationTracker()

        text = "ML is AI [1]. DL is ML [2]."
        search_results = [
            {
                "chunk_id": 101,
                "document_id": 1,
                "document_filename": "ml.pdf",
                "content": "Machine learning is artificial intelligence.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.9
            },
            {
                "chunk_id": 102,
                "document_id": 2,
                "document_filename": "dl.pdf",
                "content": "Deep learning is machine learning.",
                "chunk_index": 0,
                "page_number": 2,
                "score": 0.8
            }
        ]

        citations = tracker.map_citations_to_sources(text, search_results)

        assert len(citations) == 2
        assert citations[0]["number"] == 1
        assert citations[0]["chunk_id"] == 101
        assert citations[0]["document_filename"] == "ml.pdf"
        assert citations[1]["number"] == 2
        assert citations[1]["chunk_id"] == 102

    def test_format_citation_list_markdown(self):
        """Test Markdown citation formatting."""
        tracker = CitationTracker()

        citations = [
            {
                "number": 1,
                "document_filename": "ml.pdf",
                "page_number": 5,
                "content_preview": "Machine learning is..."
            },
            {
                "number": 2,
                "document_filename": "dl.pdf",
                "page_number": None,
                "content_preview": "Deep learning is..."
            }
        ]

        formatted = tracker.format_citation_list(citations, format_type="markdown")

        assert "## Sources" in formatted
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "ml.pdf" in formatted
        assert "Page 5" in formatted

    def test_get_citation_statistics(self):
        """Test citation statistics calculation."""
        tracker = CitationTracker()

        text = "Claim 1 [1]. Claim 2 [2]. Claim 3 [1]."  # [1] used twice
        search_results = [
            {"chunk_id": 1, "content": "Text 1", "chunk_index": 0},
            {"chunk_id": 2, "content": "Text 2", "chunk_index": 1},
            {"chunk_id": 3, "content": "Text 3", "chunk_index": 2}
        ]

        stats = tracker.get_citation_statistics(text, search_results)

        assert stats["total_citations"] == 2  # Unique citations
        assert stats["unique_citations"] == 2
        assert stats["available_sources"] == 3
        assert stats["sources_cited"] == 2
        assert stats["citation_occurrences"][1] == 2  # [1] appears twice
        assert stats["citation_occurrences"][2] == 1  # [2] appears once

    def test_remove_invalid_citations(self):
        """Test removing invalid citation markers."""
        tracker = CitationTracker()

        text = "Valid [1] and [2]. Invalid [10] and [99]."
        cleaned = tracker.remove_invalid_citations(text, max_citation_number=5)

        assert "[1]" in cleaned
        assert "[2]" in cleaned
        assert "[10]" not in cleaned
        assert "[99]" not in cleaned

    def test_renumber_citations(self):
        """Test renumbering citations."""
        tracker = CitationTracker()

        text = "Citation [1] and [2] and [3]."
        mapping = {1: 3, 2: 1, 3: 2}  # Swap numbering

        renumbered = tracker.renumber_citations(text, mapping)

        assert renumbered == "Citation [3] and [1] and [2]."

    def test_highlight_citations_markdown(self):
        """Test citation highlighting in Markdown."""
        tracker = CitationTracker()

        text = "This is a claim [1]."
        highlighted = tracker.highlight_citations(text, format_type="markdown")

        assert "**[1]**" in highlighted

    def test_highlight_citations_html(self):
        """Test citation highlighting in HTML."""
        tracker = CitationTracker()

        text = "This is a claim [1]."
        highlighted = tracker.highlight_citations(text, format_type="html")

        assert '<span class="citation">[1]</span>' in highlighted


class TestRAGIntegration:
    """Integration tests for RAG pipeline."""

    @patch('app.services.generator.OpenAI')
    @patch('app.services.search.embedding_service')
    @patch('app.services.search.vector_index')
    def test_full_rag_pipeline(self, mock_vector_index, mock_embedding, mock_openai, db_session):
        """Test complete RAG pipeline from query to answer."""
        from app.models import User, Document, Chunk
        from app.services.search import search_service
        from app.services.generator import rag_generator

        # Setup test data
        user = User(id=1, username="test", email="test@test.com",
                   hashed_password="hash", is_admin=False)
        doc = Document(id=1, filename="ml.pdf", original_filename="ml.pdf",
                      file_path="/ml.pdf", file_size=1000, job_id="123", owner_id=1)
        chunk = Chunk(id=1, document_id=1, content="Machine learning is AI.",
                     chunk_index=0, has_embedding=True)

        db_session.add_all([user, doc, chunk])
        db_session.commit()

        # Mock search
        mock_embedding.embed_text.return_value = [0.1] * 1536
        mock_vector_index.search.return_value = [(1, 0.5)]

        # Mock generation
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="ML is AI [1]."))]
        mock_response.usage = Mock(prompt_tokens=50, completion_tokens=20, total_tokens=70)
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Step 1: Search
        search_results = search_service.vector_search(
            query="What is ML?",
            k=5,
            db=db_session
        )

        assert len(search_results) > 0

        # Step 2: Generate
        result = rag_generator.generate(
            query="What is ML?",
            search_results=search_results
        )

        assert "answer" in result
        assert len(result["citations"]) > 0


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.database import SessionLocal, engine
    from app.models import Base

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
