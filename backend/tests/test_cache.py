"""
Tests for caching functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.cache import CacheService


class TestCacheService:
    """Tests for Redis caching service."""

    @patch('app.services.cache.get_redis')
    def test_query_cache_hit(self, mock_get_redis):
        """Test query cache hit."""
        mock_redis = Mock()
        mock_redis.get.return_value = '[{"chunk_id": 1, "content": "test"}]'
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        results = cache.get_query_cache(
            query="test query",
            k=5,
            search_type="hybrid",
            alpha=0.5,
            user_id=1
        )

        assert results is not None
        assert len(results) == 1
        assert results[0]["chunk_id"] == 1

    @patch('app.services.cache.get_redis')
    def test_query_cache_miss(self, mock_get_redis):
        """Test query cache miss."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        results = cache.get_query_cache(
            query="test query",
            k=5,
            search_type="hybrid",
            alpha=0.5,
            user_id=1
        )

        assert results is None

    @patch('app.services.cache.get_redis')
    def test_set_query_cache(self, mock_get_redis):
        """Test setting query cache."""
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        results = [{"chunk_id": 1, "content": "test"}]
        success = cache.set_query_cache(
            query="test query",
            k=5,
            search_type="hybrid",
            alpha=0.5,
            user_id=1,
            results=results,
            ttl=3600
        )

        assert success is True
        mock_redis.setex.assert_called_once()

    @patch('app.services.cache.get_redis')
    def test_embedding_cache_hit(self, mock_get_redis):
        """Test embedding cache hit."""
        mock_redis = Mock()
        embedding = [0.1, 0.2, 0.3] * 512  # 1536 dims
        mock_redis.get.return_value = str(embedding)
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        cached_embedding = cache.get_embedding_cache("test text")

        assert cached_embedding is not None

    @patch('app.services.cache.get_redis')
    def test_embedding_cache_miss(self, mock_get_redis):
        """Test embedding cache miss."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        cached_embedding = cache.get_embedding_cache("test text")

        assert cached_embedding is None

    @patch('app.services.cache.get_redis')
    def test_set_embedding_cache(self, mock_get_redis):
        """Test setting embedding cache."""
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        embedding = [0.1] * 1536
        success = cache.set_embedding_cache(
            text="test text",
            embedding=embedding,
            ttl=86400
        )

        assert success is True
        mock_redis.setex.assert_called_once()

    @patch('app.services.cache.get_redis')
    def test_token_blacklist(self, mock_get_redis):
        """Test token blacklisting."""
        mock_redis = Mock()
        mock_redis.exists.return_value = 1
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        # Blacklist token
        success = cache.blacklist_token("test_token", ttl=3600)
        assert success is True

        # Check if blacklisted
        is_blacklisted = cache.is_token_blacklisted("test_token")
        assert is_blacklisted is True

    @patch('app.services.cache.get_redis')
    def test_token_not_blacklisted(self, mock_get_redis):
        """Test token not blacklisted."""
        mock_redis = Mock()
        mock_redis.exists.return_value = 0
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        is_blacklisted = cache.is_token_blacklisted("test_token")
        assert is_blacklisted is False

    @patch('app.services.cache.get_redis')
    def test_invalidate_query_cache(self, mock_get_redis):
        """Test invalidating query cache."""
        mock_redis = Mock()
        mock_redis.scan_iter.return_value = [b"key1", b"key2", b"key3"]
        mock_redis.delete.return_value = 3
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        deleted = cache.invalidate_query_cache()

        assert deleted == 3
        mock_redis.delete.assert_called_once()

    @patch('app.services.cache.get_redis')
    def test_cache_statistics(self, mock_get_redis):
        """Test cache statistics."""
        mock_redis = Mock()
        mock_redis.hgetall.return_value = {
            b"query_hits": b"100",
            b"query_misses": b"20",
            b"embedding_hits": b"50",
            b"embedding_misses": b"10"
        }
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        stats = cache.get_cache_stats()

        assert stats["query_cache"]["hits"] == 100
        assert stats["query_cache"]["misses"] == 20
        assert stats["query_cache"]["hit_rate"] == 83.33
        assert stats["embedding_cache"]["hits"] == 50
        assert stats["embedding_cache"]["misses"] == 10

    @patch('app.services.cache.get_redis')
    def test_clear_all_caches(self, mock_get_redis):
        """Test clearing all caches."""
        mock_redis = Mock()
        mock_redis.scan_iter.return_value = [b"key1", b"key2"]
        mock_redis.delete.return_value = 2
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        results = cache.clear_all_caches()

        assert "query_cache" in results
        assert "embedding_cache" in results
        assert "token_blacklist" in results

    @patch('app.services.cache.get_redis')
    def test_hash_query_consistency(self, mock_get_redis):
        """Test that same query parameters produce same hash."""
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        hash1 = cache._hash_query("test query", 5, "hybrid", 0.5, 1)
        hash2 = cache._hash_query("test query", 5, "hybrid", 0.5, 1)

        assert hash1 == hash2

    @patch('app.services.cache.get_redis')
    def test_hash_query_different_params(self, mock_get_redis):
        """Test that different query parameters produce different hashes."""
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        cache = CacheService()

        hash1 = cache._hash_query("test query", 5, "hybrid", 0.5, 1)
        hash2 = cache._hash_query("test query", 10, "hybrid", 0.5, 1)  # Different k

        assert hash1 != hash2


class TestCacheIntegration:
    """Integration tests for caching with search."""

    @patch('app.services.cache.get_redis')
    @patch('app.services.search.embedding_service')
    @patch('app.services.search.vector_index')
    def test_search_with_cache(self, mock_vector_index, mock_embedding, mock_get_redis, db_session):
        """Test search with caching enabled."""
        from app.models import User, Document, Chunk
        from app.services.search import search_service

        # Setup test data
        user = User(id=1, username="test", email="test@test.com",
                   hashed_password="hash", is_admin=False)
        doc = Document(id=1, filename="test.pdf", original_filename="test.pdf",
                      file_path="/test", file_size=100, job_id="123", owner_id=1)
        chunk = Chunk(id=1, document_id=1, content="Test content",
                     chunk_index=0, has_embedding=True)

        db_session.add_all([user, doc, chunk])
        db_session.commit()

        # Mock Redis
        mock_redis = Mock()
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.return_value = True
        mock_redis.hincrby.return_value = 1
        mock_get_redis.return_value = mock_redis

        # Mock search
        mock_embedding.embed_text.return_value = [0.1] * 1536
        mock_vector_index.search.return_value = [(1, 0.5)]

        # First search (cache miss)
        results1 = search_service.search(
            query="test",
            k=5,
            search_type="vector",
            user_id=1,
            db=db_session,
            use_cache=True
        )

        assert len(results1) > 0

        # Verify setex was called to cache results
        assert mock_redis.setex.called

    @patch('app.services.cache.get_redis')
    def test_logout_blacklists_token(self, mock_get_redis):
        """Test that logout blacklists the token."""
        from app.services.cache import cache_service

        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        token = "test_token_xyz"

        # Blacklist token
        cache_service.blacklist_token(token, ttl=3600)

        # Verify setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # TTL
        assert call_args[0][2] == "blacklisted"


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
