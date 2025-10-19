"""
Citation tracking and validation service.
Manages source references and citation integrity for RAG responses.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger(__name__)


class CitationTracker:
    """
    Service for tracking and validating citations in RAG responses.

    Features:
    - Extract citation markers from text
    - Validate citation references
    - Map citations to source documents
    - Generate citation metadata
    """

    def __init__(self):
        """Initialize citation tracker."""
        self.citation_pattern = r'\[(\d+)\]'

    def extract_citations(self, text: str) -> List[int]:
        """
        Extract all citation numbers from text.

        Args:
            text: Text containing citation markers like [1], [2], etc.

        Returns:
            List of citation numbers (sorted, unique)
        """
        matches = re.findall(self.citation_pattern, text)
        citation_numbers = sorted(set(int(num) for num in matches))

        logger.debug(f"Extracted {len(citation_numbers)} unique citations from text")
        return citation_numbers

    def validate_citations(
        self,
        text: str,
        max_citation_number: int
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all citations in text are within valid range.

        Args:
            text: Text containing citations
            max_citation_number: Maximum valid citation number

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        citations = self.extract_citations(text)
        errors = []

        for citation_num in citations:
            if citation_num < 1:
                errors.append(f"Invalid citation number: [{citation_num}] (must be >= 1)")
            elif citation_num > max_citation_number:
                errors.append(
                    f"Citation [{citation_num}] exceeds available sources "
                    f"(max: [{max_citation_number}])"
                )

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(f"Citation validation failed: {errors}")

        return is_valid, errors

    def map_citations_to_sources(
        self,
        text: str,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map citation numbers to their source documents.

        Args:
            text: Text containing citations
            search_results: Search results used as sources

        Returns:
            List of citation metadata dictionaries
        """
        citation_numbers = self.extract_citations(text)
        citations = []

        for citation_num in citation_numbers:
            idx = citation_num - 1  # Convert to 0-based index

            if 0 <= idx < len(search_results):
                source = search_results[idx]

                citations.append({
                    "number": citation_num,
                    "chunk_id": source.get("chunk_id"),
                    "document_id": source.get("document_id"),
                    "document_filename": source.get("document_filename", "Unknown"),
                    "page_number": source.get("page_number"),
                    "chunk_index": source.get("chunk_index"),
                    "score": source.get("score", 0.0),
                    "content": source.get("content", ""),
                    "content_preview": source.get("content", "")[:200] + "..."
                })
            else:
                logger.warning(
                    f"Citation [{citation_num}] out of range "
                    f"(available sources: {len(search_results)})"
                )

        return citations

    def format_citation_list(
        self,
        citations: List[Dict[str, Any]],
        format_type: str = "markdown"
    ) -> str:
        """
        Format citations as a readable list.

        Args:
            citations: List of citation dictionaries
            format_type: "markdown", "html", or "plain"

        Returns:
            Formatted citation list string
        """
        if not citations:
            return "No citations."

        if format_type == "markdown":
            return self._format_citations_markdown(citations)
        elif format_type == "html":
            return self._format_citations_html(citations)
        else:
            return self._format_citations_plain(citations)

    def _format_citations_markdown(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations as Markdown list."""
        lines = ["## Sources\n"]

        for citation in citations:
            num = citation["number"]
            filename = citation["document_filename"]
            page = citation.get("page_number")

            citation_line = f"[{num}] **{filename}**"
            if page:
                citation_line += f" (Page {page})"

            # Add content preview
            preview = citation.get("content_preview", "")
            if preview:
                citation_line += f"\n   > {preview}"

            lines.append(citation_line)

        return "\n".join(lines)

    def _format_citations_html(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations as HTML list."""
        lines = ["<div class='citations'>", "<h3>Sources</h3>", "<ol>"]

        for citation in citations:
            filename = citation["document_filename"]
            page = citation.get("page_number")

            citation_html = f"<li><strong>{filename}</strong>"
            if page:
                citation_html += f" (Page {page})"

            preview = citation.get("content_preview", "")
            if preview:
                citation_html += f"<br><em>{preview}</em>"

            citation_html += "</li>"
            lines.append(citation_html)

        lines.extend(["</ol>", "</div>"])
        return "\n".join(lines)

    def _format_citations_plain(self, citations: List[Dict[str, Any]]) -> str:
        """Format citations as plain text list."""
        lines = ["SOURCES:", ""]

        for citation in citations:
            num = citation["number"]
            filename = citation["document_filename"]
            page = citation.get("page_number")

            citation_line = f"[{num}] {filename}"
            if page:
                citation_line += f" (Page {page})"

            lines.append(citation_line)

        return "\n".join(lines)

    def get_citation_statistics(
        self,
        text: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get statistics about citations in the text.

        Args:
            text: Text containing citations
            search_results: Available search results

        Returns:
            Dictionary with citation statistics
        """
        citation_numbers = self.extract_citations(text)
        citations = self.map_citations_to_sources(text, search_results)

        # Count citation occurrences
        citation_occurrences = {}
        for match in re.finditer(self.citation_pattern, text):
            num = int(match.group(1))
            citation_occurrences[num] = citation_occurrences.get(num, 0) + 1

        # Calculate coverage (what % of sources were cited)
        coverage = len(citation_numbers) / len(search_results) if search_results else 0

        return {
            "total_citations": len(citation_numbers),
            "unique_citations": len(set(citation_numbers)),
            "citation_occurrences": citation_occurrences,
            "available_sources": len(search_results),
            "sources_cited": len(citations),
            "coverage_percentage": round(coverage * 100, 2),
            "citation_numbers": citation_numbers
        }

    def remove_invalid_citations(
        self,
        text: str,
        max_citation_number: int
    ) -> str:
        """
        Remove invalid citation markers from text.

        Args:
            text: Text containing citations
            max_citation_number: Maximum valid citation number

        Returns:
            Text with invalid citations removed
        """
        def replace_citation(match):
            num = int(match.group(1))
            if 1 <= num <= max_citation_number:
                return match.group(0)  # Keep valid citation
            else:
                logger.warning(f"Removing invalid citation: [{num}]")
                return ""  # Remove invalid citation

        cleaned_text = re.sub(self.citation_pattern, replace_citation, text)
        return cleaned_text

    def renumber_citations(
        self,
        text: str,
        mapping: Dict[int, int]
    ) -> str:
        """
        Renumber citations according to a mapping.

        Useful for reordering sources or removing duplicates.

        Args:
            text: Text containing citations
            mapping: Dictionary mapping old citation numbers to new ones

        Returns:
            Text with renumbered citations
        """
        def replace_citation(match):
            old_num = int(match.group(1))
            new_num = mapping.get(old_num, old_num)
            return f"[{new_num}]"

        renumbered_text = re.sub(self.citation_pattern, replace_citation, text)

        logger.debug(f"Renumbered citations using mapping: {mapping}")
        return renumbered_text

    def highlight_citations(
        self,
        text: str,
        format_type: str = "markdown"
    ) -> str:
        """
        Highlight citations in text for better readability.

        Args:
            text: Text containing citations
            format_type: "markdown", "html", or "ansi"

        Returns:
            Text with highlighted citations
        """
        if format_type == "markdown":
            # Make citations bold
            return re.sub(self.citation_pattern, r'**[\1]**', text)
        elif format_type == "html":
            # Wrap in span with class
            return re.sub(
                self.citation_pattern,
                r'<span class="citation">[\1]</span>',
                text
            )
        elif format_type == "ansi":
            # Use ANSI color codes
            return re.sub(self.citation_pattern, r'\033[1;36m[\1]\033[0m', text)
        else:
            return text


# Global instance
citation_tracker = CitationTracker()
