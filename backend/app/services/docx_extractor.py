"""
DOCX extractor service for extracting structured text from Word documents.
Preserves paragraphs, headings, lists, and tables while extracting text.
"""

try:
    from docx import Document
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    Document = None

from typing import Dict, Any, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DocxExtractor:
    """Service for extracting structured text from DOCX files."""

    def __init__(self):
        """Initialize DOCX extractor."""
        self.enabled = DOCX_AVAILABLE

        if not self.enabled:
            logger.warning(
                "python-docx is not available. DOCX extraction will be disabled. "
                "Install python-docx to enable DOCX processing."
            )

    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from a DOCX file with structure preservation.

        Args:
            file_path: Path to the DOCX file

        Returns:
            Dictionary with extracted text, structure, and metadata
            {
                "text": str,                    # Full text with preserved formatting
                "paragraphs": List[Dict],       # Individual paragraphs with metadata
                "tables": List[Dict],           # Extracted tables
                "metadata": Dict,               # Document metadata
                "error": Optional[str]
            }

        Raises:
            FileNotFoundError: If DOCX file doesn't exist
            Exception: If extraction fails
        """
        result = {
            "text": "",
            "paragraphs": [],
            "tables": [],
            "metadata": {},
            "error": None
        }

        # Check if python-docx is available
        if not self.enabled:
            error_msg = (
                "python-docx is not installed. "
                "Please install python-docx to process DOCX files. "
                "Run: pip install python-docx"
            )
            logger.error(error_msg)
            result["error"] = error_msg
            raise Exception(error_msg)

        try:
            # Check if file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"DOCX file not found: {file_path}")

            # Open document
            logger.info(f"Processing DOCX file: {file_path}")
            doc = Document(file_path)

            # Extract document properties
            result["metadata"] = self._extract_metadata(doc)

            # Extract content with structure
            structured_content = self._extract_structured_content(doc)
            result["paragraphs"] = structured_content["paragraphs"]
            result["tables"] = structured_content["tables"]

            # Build full text with preserved structure
            result["text"] = self._build_formatted_text(
                structured_content["paragraphs"],
                structured_content["tables"]
            )

            logger.info(
                f"DOCX extracted: {len(result['paragraphs'])} paragraphs, "
                f"{len(result['tables'])} tables, "
                f"{len(result['text'])} characters"
            )

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            result["error"] = str(e)
            raise

        return result

    def _extract_metadata(self, doc: Document) -> Dict[str, Any]:
        """
        Extract document metadata from DOCX core properties.

        Args:
            doc: Document object

        Returns:
            Dictionary with metadata
        """
        metadata = {}

        try:
            props = doc.core_properties
            metadata["title"] = props.title or ""
            metadata["author"] = props.author or ""
            metadata["subject"] = props.subject or ""
            metadata["created"] = str(props.created) if props.created else None
            metadata["modified"] = str(props.modified) if props.modified else None
            metadata["last_modified_by"] = props.last_modified_by or ""
        except Exception as e:
            logger.warning(f"Could not extract document properties: {e}")

        return metadata

    def _extract_structured_content(self, doc: Document) -> Dict[str, Any]:
        """
        Extract content while preserving document structure.

        Args:
            doc: Document object

        Returns:
            Dictionary with structured content
        """
        paragraphs = []
        tables = []
        para_index = 0
        table_index = 0

        # Iterate through document elements in order
        for element in doc.element.body:
            if isinstance(element, CT_P):
                # It's a paragraph
                para = Paragraph(element, doc)
                para_data = self._extract_paragraph(para, para_index)
                if para_data:  # Skip empty paragraphs
                    paragraphs.append(para_data)
                    para_index += 1

            elif isinstance(element, CT_Tbl):
                # It's a table
                table = Table(element, doc)
                table_data = self._extract_table(table, table_index)
                if table_data:
                    tables.append(table_data)
                    table_index += 1

        return {
            "paragraphs": paragraphs,
            "tables": tables
        }

    def _extract_paragraph(self, para: Paragraph, index: int) -> Dict[str, Any]:
        """
        Extract paragraph with metadata.

        Args:
            para: Paragraph object
            index: Paragraph index

        Returns:
            Dictionary with paragraph data
        """
        text = para.text.strip()
        if not text:
            return None

        # Detect paragraph style/type
        style = para.style.name if para.style else "Normal"
        is_heading = style.startswith("Heading")
        heading_level = None

        if is_heading:
            try:
                heading_level = int(style.split()[-1])
            except (ValueError, IndexError):
                heading_level = 1

        return {
            "text": text,
            "index": index,
            "style": style,
            "is_heading": is_heading,
            "heading_level": heading_level,
            "is_list_item": self._is_list_item(para)
        }

    def _is_list_item(self, para: Paragraph) -> bool:
        """
        Check if paragraph is a list item.

        Args:
            para: Paragraph object

        Returns:
            True if paragraph is a list item
        """
        try:
            # Check for numbering/bullets
            return para._element.pPr is not None and para._element.pPr.numPr is not None
        except Exception:
            return False

    def _extract_table(self, table: Table, index: int) -> Dict[str, Any]:
        """
        Extract table data.

        Args:
            table: Table object
            index: Table index

        Returns:
            Dictionary with table data
        """
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)

        if not rows:
            return None

        # Convert table to text representation
        table_text = self._table_to_text(rows)

        return {
            "index": index,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(rows[0]) if rows else 0,
            "text": table_text
        }

    def _table_to_text(self, rows: List[List[str]]) -> str:
        """
        Convert table rows to formatted text.

        Args:
            rows: List of row data

        Returns:
            Formatted table text
        """
        if not rows:
            return ""

        # Simple markdown-like table format
        lines = []
        for i, row in enumerate(rows):
            line = " | ".join(row)
            lines.append(line)
            # Add separator after header row
            if i == 0:
                lines.append("-" * len(line))

        return "\n".join(lines)

    def _build_formatted_text(
        self,
        paragraphs: List[Dict[str, Any]],
        tables: List[Dict[str, Any]]
    ) -> str:
        """
        Build formatted text with preserved structure.

        Args:
            paragraphs: List of paragraph dictionaries
            tables: List of table dictionaries

        Returns:
            Formatted text string
        """
        lines = []

        # Create a map of table indices for insertion
        table_map = {t["index"]: t for t in tables}

        for para in paragraphs:
            # Add proper spacing for headings
            if para["is_heading"]:
                if lines:  # Add spacing before heading
                    lines.append("")

                # Format heading with markdown-style markers
                level = para["heading_level"] or 1
                heading_marker = "#" * level
                lines.append(f"{heading_marker} {para['text']}")
                lines.append("")  # Add spacing after heading

            # Format list items
            elif para["is_list_item"]:
                lines.append(f"• {para['text']}")

            # Regular paragraph
            else:
                if lines and lines[-1] and not lines[-1].startswith("#"):
                    lines.append("")  # Add spacing between paragraphs
                lines.append(para["text"])

        # Add tables at the end (or we could track their original positions)
        if tables:
            lines.append("")
            lines.append("## Tables")
            lines.append("")
            for table in tables:
                lines.append(f"### Table {table['index'] + 1}")
                lines.append(table["text"])
                lines.append("")

        return "\n".join(lines)


# Global instance
docx_extractor = DocxExtractor()
