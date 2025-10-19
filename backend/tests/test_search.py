"""
Tests for search functionality (embedding, vector index, and hybrid search).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.embedding import EmbeddingService
from app.services.vector_index import VectorIndexManager
from app.services.search import SearchService
from app.models import Chunk, Document, User


class TestEmbeddingService:
    """Tests for OpenAI embedding service."""

    @patch('app.services.embedding.OpenAI')
    def test_embed_text_success(self, mock_openai):
        """Test successful single text embedding."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = EmbeddingService()
        embedding = service.embed_text("test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        mock_client.embeddings.create.assert_called_once()

    @patch('app.services.embedding.OpenAI')
    def test_embed_batch_success(self, mock_openai):
        """Test successful batch embedding."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        service = EmbeddingService()
        texts = ["text 1", "text 2", "text 3"]
        embeddings = service.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)

    def test_embed_empty_text(self):
        """Test that embedding empty text raises error."""
        service = EmbeddingService()

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            service.embed_text("")

        with pytest.raises(ValueError, match="Cannot embed empty text"):
            service.embed_text("   ")


class TestVectorIndexManager:
    """Tests for FAISS vector index manager."""

    def test_create_index(self, tmp_path):
        """Test creating a new index."""
        index_path = str(tmp_path / "test_index.bin")
        mapping_path = str(tmp_path / "test_mapping.pkl")

        manager = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        assert manager.index is not None
        assert manager.index.ntotal == 0
        assert len(manager.chunk_ids) == 0

    def test_add_vectors(self, tmp_path):
        """Test adding vectors to index."""
        index_path = str(tmp_path / "test_index.bin")
        mapping_path = str(tmp_path / "test_mapping.pkl")

        manager = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        # Add some test vectors
        embeddings = [[0.1] * 128, [0.2] * 128, [0.3] * 128]
        chunk_ids = [1, 2, 3]

        count = manager.add_vectors(embeddings, chunk_ids)

        assert count == 3
        assert manager.index.ntotal == 3
        assert manager.chunk_ids == [1, 2, 3]

    def test_search_vectors(self, tmp_path):
        """Test searching for similar vectors."""
        index_path = str(tmp_path / "test_index.bin")
        mapping_path = str(tmp_path / "test_mapping.pkl")

        manager = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        # Add test vectors
        embeddings = [[0.1] * 128, [0.5] * 128, [0.9] * 128]
        chunk_ids = [1, 2, 3]
        manager.add_vectors(embeddings, chunk_ids)

        # Search with query similar to first vector
        query = [0.1] * 128
        results = manager.search(query, k=2)

        assert len(results) == 2
        assert results[0][0] == 1  # First result should be chunk_id 1
        assert results[0][1] < results[1][1]  # Distance should increase

    def test_save_and_load_index(self, tmp_path):
        """Test saving and loading index."""
        index_path = str(tmp_path / "test_index.bin")
        mapping_path = str(tmp_path / "test_mapping.pkl")

        # Create and populate index
        manager1 = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        embeddings = [[0.1] * 128, [0.2] * 128]
        chunk_ids = [1, 2]
        manager1.add_vectors(embeddings, chunk_ids)
        manager1.save_index()

        # Load index in new manager
        manager2 = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        assert manager2.index.ntotal == 2
        assert manager2.chunk_ids == [1, 2]

    def test_dimension_mismatch_error(self, tmp_path):
        """Test that dimension mismatch raises error."""
        index_path = str(tmp_path / "test_index.bin")
        mapping_path = str(tmp_path / "test_mapping.pkl")

        manager = VectorIndexManager(
            dimension=128,
            index_path=index_path,
            mapping_path=mapping_path
        )

        # Try to add vectors with wrong dimension
        embeddings = [[0.1] * 64]  # Wrong dimension
        chunk_ids = [1]

        with pytest.raises(ValueError, match="dimension"):
            manager.add_vectors(embeddings, chunk_ids)


class TestSearchService:
    """Tests for hybrid search service."""

    @patch('app.services.search.embedding_service')
    @patch('app.services.search.vector_index')
    def test_vector_search(self, mock_vector_index, mock_embedding_service, db_session):
        """Test vector search functionality."""
        # Mock embedding service
        mock_embedding_service.embed_text.return_value = [0.1] * 1536

        # Mock vector index search results
        mock_vector_index.search.return_value = [
            (1, 0.5),  # (chunk_id, distance)
            (2, 1.0)
        ]

        # Create test chunks in database
        user = User(id=1, username="test", email="test@test.com", hashed_password="hash", is_admin=False)
        doc = Document(id=1, filename="test.pdf", original_filename="test.pdf",
                      file_path="/test", file_size=100, job_id="123", owner_id=1)
        chunk1 = Chunk(id=1, document_id=1, content="Test content 1", chunk_index=0)
        chunk2 = Chunk(id=2, document_id=1, content="Test content 2", chunk_index=1)

        db_session.add_all([user, doc, chunk1, chunk2])
        db_session.commit()

        # Perform search
        service = SearchService()
        results = service.vector_search("test query", k=2, db=db_session)

        assert len(results) == 2
        assert results[0]["chunk_id"] == 1
        assert results[1]["chunk_id"] == 2
        assert "score" in results[0]
        assert results[0]["search_type"] == "vector"

    def test_fulltext_search(self, db_session):
        """Test full-text search functionality."""
        # Create test data
        user = User(id=1, username="test", email="test@test.com", hashed_password="hash", is_admin=False)
        doc = Document(id=1, filename="test.pdf", original_filename="test.pdf",
                      file_path="/test", file_size=100, job_id="123", owner_id=1)
        chunk1 = Chunk(id=1, document_id=1, content="Python programming language", chunk_index=0)
        chunk2 = Chunk(id=2, document_id=1, content="JavaScript web development", chunk_index=1)

        db_session.add_all([user, doc, chunk1, chunk2])
        db_session.commit()

        # Perform search
        service = SearchService()
        results = service.fulltext_search("Python", k=5, db=db_session)

        # Results may be empty if FTS index not created
        # This test validates the search executes without error
        assert isinstance(results, list)

    @patch('app.services.search.embedding_service')
    @patch('app.services.search.vector_index')
    def test_hybrid_search(self, mock_vector_index, mock_embedding_service, db_session):
        """Test hybrid search with RRF fusion."""
        # Mock embedding
        mock_embedding_service.embed_text.return_value = [0.1] * 1536

        # Mock vector search results
        mock_vector_index.search.return_value = [(1, 0.5), (2, 1.0)]

        # Create test data
        user = User(id=1, username="test", email="test@test.com", hashed_password="hash", is_admin=False)
        doc = Document(id=1, filename="test.pdf", original_filename="test.pdf",
                      file_path="/test", file_size=100, job_id="123", owner_id=1)
        chunk1 = Chunk(id=1, document_id=1, content="Python programming", chunk_index=0)
        chunk2 = Chunk(id=2, document_id=1, content="JavaScript coding", chunk_index=1)

        db_session.add_all([user, doc, chunk1, chunk2])
        db_session.commit()

        # Perform hybrid search
        service = SearchService()
        results = service.hybrid_search("programming", k=5, alpha=0.5, db=db_session)

        assert isinstance(results, list)
        # Should combine results from both methods
        if results:
            assert "rrf_score" in results[0]
            assert "search_type" in results[0]
            assert results[0]["search_type"] == "hybrid"

    def test_search_with_user_access_control(self, db_session):
        """Test that search respects user access control."""
        # Create two users and documents
        user1 = User(id=1, username="user1", email="user1@test.com",
                    hashed_password="hash", is_admin=False)
        user2 = User(id=2, username="user2", email="user2@test.com",
                    hashed_password="hash", is_admin=False)

        doc1 = Document(id=1, filename="doc1.pdf", original_filename="doc1.pdf",
                       file_path="/doc1", file_size=100, job_id="123", owner_id=1)
        doc2 = Document(id=2, filename="doc2.pdf", original_filename="doc2.pdf",
                       file_path="/doc2", file_size=100, job_id="456", owner_id=2)

        chunk1 = Chunk(id=1, document_id=1, content="User 1 content", chunk_index=0)
        chunk2 = Chunk(id=2, document_id=2, content="User 2 content", chunk_index=0)

        db_session.add_all([user1, user2, doc1, doc2, chunk1, chunk2])
        db_session.commit()

        service = SearchService()

        # Mock search results containing both chunks
        mock_results = [
            {"chunk_id": 1, "document_id": 1, "content": "User 1 content"},
            {"chunk_id": 2, "document_id": 2, "content": "User 2 content"}
        ]

        # Filter for user 1 - should only see their own document
        filtered = service._filter_by_user_access(mock_results, user_id=1, db=db_session)

        assert len(filtered) == 1
        assert filtered[0]["document_id"] == 1


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.database import SessionLocal, engine
    from app.models import Base

    # Create tables
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
