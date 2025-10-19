"""
GPT-4 generation service for Retrieval-Augmented Generation (RAG).
Generates answers with citations based on retrieved context.
"""

import logging
from typing import List, Dict, Any, Iterator, Optional
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class RAGGenerator:
    """
    Service for generating answers using GPT-4 with retrieved context.

    Features:
    - Context-aware answer generation
    - Citation tracking with [1], [2], etc.
    - Streaming support for real-time responses
    - Configurable models and parameters
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 1000
    ):
        """
        Initialize RAG generator.

        Args:
            model: OpenAI model to use (gpt-4o-mini, gpt-4o, gpt-4-turbo)
            temperature: Sampling temperature (0-2, lower = more focused)
            max_tokens: Maximum tokens in response
        """
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_system_prompt(self) -> str:
        """
        Build system prompt for RAG.

        Returns:
            System prompt string
        """
        return """You are a helpful AI assistant that answers questions based on provided context from documents.

IMPORTANT INSTRUCTIONS:
1. Answer questions using ONLY the information from the provided context
2. Use citations in the format [1], [2], etc. to reference specific sources
3. If the context doesn't contain enough information, say "I don't have enough information in the provided documents to answer that question"
4. Always cite your sources when making claims
5. If multiple sources support a claim, cite all of them: [1][2]

FORMATTING GUIDELINES:
- Structure your answer with clear paragraphs (use double line breaks between paragraphs)
- Use bullet points or numbered lists when listing multiple items
- Start with a brief overview paragraph if the question is complex
- Break down long explanations into digestible sections
- Use proper spacing and formatting to make the answer easy to read

CRITICAL LIST FORMATTING RULES:
1. For numbered lists: Put ALL content on the SAME line as the number
   Format: "1. Description goes here on same line"

2. For bullet lists: Put ALL content on the SAME line as the bullet
   Format: "- Description goes here on same line"

3. NEVER use this pattern:
   1. **Title**:
      - Details
   This breaks list rendering!

4. ALWAYS use this pattern instead:
   1. Title - details go here on the same line
   2. Another item - more details on this line

CORRECT EXAMPLES:
1. MapReduce Framework - a programming model for processing large datasets
2. Hadoop Clusters - distributed computing infrastructure for big data
3. YARN - resource management component in Hadoop

INCORRECT (NEVER USE):
1. **MapReduce Framework**:
   - A programming model for processing large datasets

Example Answer:
Machine learning is a subset of artificial intelligence that enables systems to learn from data [1]. These algorithms have the unique ability to improve their performance over time without explicit programming [2].

Common applications include:

1. Image recognition - identifying and classifying objects in photos and videos
2. Natural language processing - understanding and generating human language
3. Predictive analytics - analyzing patterns to forecast future trends and behaviors

All of these applications leverage ML's ability to learn from data [3].
"""

    def _format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Format search results into context for the prompt.

        Args:
            search_results: List of search results with content and metadata

        Returns:
            Formatted context string with source references
        """
        if not search_results:
            return "No context available."

        context_parts = []

        for idx, result in enumerate(search_results, start=1):
            # Extract relevant information
            content = result.get("content", "")
            doc_name = result.get("document_filename", "Unknown")
            page = result.get("page_number")
            chunk_idx = result.get("chunk_index", 0)

            # Format source reference
            source_ref = f"[{idx}] "
            source_info = f"(Source: {doc_name}"
            if page:
                source_info += f", Page {page}"
            source_info += f", Section {chunk_idx + 1})"

            # Build context entry
            context_entry = f"{source_ref}{content}\n{source_info}"
            context_parts.append(context_entry)

        return "\n\n".join(context_parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        """
        Build user prompt with query and context.

        Args:
            query: User's question
            context: Formatted context from search results

        Returns:
            User prompt string
        """
        return f"""Context from documents:

{context}

---

Question: {query}

Please provide a comprehensive answer based on the context above, using citations [1], [2], etc."""

    def generate(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate answer using GPT-4 (non-streaming).

        Args:
            query: User's question
            search_results: Retrieved context chunks
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Dictionary with answer, citations, and metadata
        """
        if not search_results:
            return {
                "answer": "I don't have any relevant documents to answer this question.",
                "citations": [],
                "model": self.model,
                "usage": {}
            }

        # Format context
        context = self._format_context(search_results)

        # Build messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(query, context)}
        ]

        # Generate response
        try:
            logger.info(f"Generating answer with {model or self.model}")

            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=False
            )

            answer = response.choices[0].message.content

            # Extract usage information
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            logger.info(
                f"Answer generated: {len(answer)} chars, "
                f"{usage['total_tokens']} tokens"
            )

            return {
                "answer": answer,
                "citations": self._extract_citations(answer, search_results),
                "model": model or self.model,
                "usage": usage,
                "context_used": len(search_results)
            }

        except Exception as e:
            logger.error(f"Answer generation failed: {e}", exc_info=True)
            raise

    def generate_stream(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """
        Generate answer using GPT-4 with streaming.

        Yields answer chunks in real-time as they're generated.

        Args:
            query: User's question
            search_results: Retrieved context chunks
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Yields:
            Answer chunks (strings)
        """
        if not search_results:
            yield "I don't have any relevant documents to answer this question."
            return

        # Format context
        context = self._format_context(search_results)

        # Build messages
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_prompt(query, context)}
        ]

        # Generate streaming response
        try:
            logger.info(f"Streaming answer with {model or self.model}")

            stream = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming answer generation failed: {e}", exc_info=True)
            yield f"\n\n[Error: {str(e)}]"

    def _extract_citations(
        self,
        answer: str,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract citations from answer text.

        Finds citation markers like [1], [2], etc. and maps them to sources.

        Args:
            answer: Generated answer text
            search_results: Search results used as context

        Returns:
            List of citation dictionaries
        """
        import re

        citations = []

        # Find all citation markers [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        found_citations = set(re.findall(citation_pattern, answer))

        for citation_num in sorted(found_citations, key=int):
            idx = int(citation_num) - 1  # Convert to 0-based index

            if 0 <= idx < len(search_results):
                result = search_results[idx]

                citations.append({
                    "citation_number": int(citation_num),
                    "chunk_id": result.get("chunk_id"),
                    "document_id": result.get("document_id"),
                    "document_filename": result.get("document_filename", "Unknown"),
                    "page_number": result.get("page_number"),
                    "chunk_index": result.get("chunk_index"),
                    "content_preview": result.get("content", "")[:200] + "..."
                })

        logger.debug(f"Extracted {len(citations)} citations from answer")
        return citations


# Global instance
rag_generator = RAGGenerator()
