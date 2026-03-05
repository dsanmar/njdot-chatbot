"""Section-aware chunker for NJDOT PDF documents.

Consumes the list of page dicts produced by ``PDFParser.extract_text()`` and
emits a flat list of chunk dicts ready for embedding and storage.

Three document types are supported via the ``doc_type`` parameter:

``"specs"`` (default) — Standard Specifications for Road and Bridge Work
    * Skip PDF pages 1–34          (front-matter / TOC)
    * Skip index pages             (last 30 pages of the PDF)
    * Primary boundaries: SUBSECTION (XXX.XX) and SUB_SUBSECTION (XXX.XX.YY)
      headings.  Each chunk contains the text of one subsection.
    * DIVISION heading: updates division tracker only (no new chunk).
    * SECTION heading: flushes any open chunk, updates section tracker,
      does not open a new chunk (content before the first subsection is
      discarded).

``"scheduling"`` — Construction Scheduling Manual
    * Skip pages 1–2       (cover + TOC; ``front_matter_pages=2``)
    * No index tail skip   (``index_tail_pages=0``)
    * Primary boundary: ``decimal_section`` heading (e.g. "7.0 Designer …").

``"material_proc"`` — NJDOT Material Procedure files (MP*.pdf)
    * No page skipping (short 4–7 page files; ``front_matter_pages=0``)
    * No index tail skip   (``index_tail_pages=0``)
    * ``boundary_level="none"``: the ENTIRE document is treated as one block.
    * ``section_id``    = the doc name supplied via ``doc_name=`` (e.g. ``"MP1-25"``).
    * ``section_title`` = first all-caps line with ≥4 words found in the text
                          (the human-readable procedure title).
    * ``division``      = ``"MATERIAL PROCEDURES"`` (fixed).

Filtering rules (both types)
-----------------------------
* Skip blank pages             (empty text or ``[NO TEXT]`` sentinel)
* Skip TOC artifact pages      (last non-empty line is a "doubled" page number,
                                e.g. ``"113113"`` where ``"113"`` appears twice)

Shared chunking rules
---------------------
* Max 750 tokens per chunk (tiktoken ``cl100k_base`` encoding).
* 100-token overlap when a section must be split across multiple chunks.
* Printed page number is extracted from the last non-empty line of each page
  when it is a bare integer; otherwise derived as ``pdf_page − front_matter_pages``.
* The very first line of every chunk's content is always
  ``"<section_id> <section_title>"`` — even for continuation chunks produced
  by splitting an over-length section.

Chunk output schema
-------------------
Each returned dict has two keys:

``content`` : str
    The full text of the chunk, beginning with ``section_id  section_title``.

``metadata`` : dict
    section_id    – subsection/sub-subsection id, e.g. ``"902.02"`` or ``"902.02.03"``
    section_title – subsection title, e.g. ``"Mix Design"``
    division      – division title, e.g. ``"HOT MIX ASPHALT"``
    page_pdf      – PDF page number where this chunk begins (int)
    page_printed  – Printed page number on that page (int)
    kind          – always ``"text"``

Usage
-----
    from app.ingestion.pdf_parser import PDFParser
    from app.ingestion.chunker import Chunker

    pages  = PDFParser("path/to/doc.pdf").extract_text()
    chunks = Chunker().chunk(pages)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import tiktoken

# ── Import section_detector, supporting both module (-m) and script execution.
try:
    from app.ingestion.section_detector import detect
except ImportError:
    # Running directly as a script; put the package root on sys.path.
    _pkg_root = str(Path(__file__).resolve().parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    from app.ingestion.section_detector import detect  # type: ignore[no-redef]


# ── Module-level constants ────────────────────────────────────────────────────

FRONT_MATTER_PAGES: int = 34   # pages 1..34 are TOC / front matter  (specs)
INDEX_TAIL_PAGES:   int = 30   # last 30 pages are index              (specs)
MAX_TOKENS:         int = 750
OVERLAP_TOKENS:     int = 100
ENCODING_NAME:      str = "cl100k_base"

_BARE_INT_RE = re.compile(r'^\d+$')

# Matches lines that are entirely upper-case letters, spaces, and common
# punctuation — used to detect MP procedure titles such as
# "FIELD INSPECTION AND TESTING OF CONCRETE".
_ALL_CAPS_TITLE_RE = re.compile(r'^[A-Z][A-Z\s()/\-]+$')

# ── Per-document-type defaults ────────────────────────────────────────────────
#
# These drive the Chunker constructor defaults when doc_type is supplied.
# Keys: front_matter_pages, index_tail_pages, boundary_level
#   boundary_level is the detect() level that opens a new chunk.

_DOC_PROFILES: dict[str, dict] = {
    "specs": {
        "front_matter_pages": FRONT_MATTER_PAGES,  # 34
        "index_tail_pages":   INDEX_TAIL_PAGES,    # 30
        # Both XXX.XX and XXX.XX.YY headings open a new chunk.
        "boundary_levels": frozenset({"subsection", "sub_subsection"}),
    },
    "scheduling": {
        "front_matter_pages": 2,   # skip cover (p.1) + TOC (p.2)
        "index_tail_pages":   0,
        "boundary_levels": frozenset({"decimal_section"}),
    },
    "material_proc": {
        "front_matter_pages": 0,   # short 4–7 page files; no front matter
        "index_tail_pages":   0,
        "boundary_levels": frozenset(),  # empty = whole doc as one block
    },
}


# ── Module-level encoder (shared; avoids repeated initialisation) ─────────────

def _get_encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING_NAME)


# ── Page-level helpers ────────────────────────────────────────────────────────

def _is_blank(text: str) -> bool:
    """Return True for pages with no usable text."""
    stripped = text.strip()
    return stripped == "" or stripped == "[NO TEXT]"


def _is_doubled_page_num(lines: List[str]) -> bool:
    """
    Return True when the last non-empty line is a TOC artifact where a page
    number is concatenated with itself (e.g. ``"113113"`` for page 113).

    We require the repeated unit to be at least **2 characters** so that
    ordinary two-digit page numbers such as ``"11"`` are never mis-classified.
    """
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Last non-empty line must be all digits
        if not _BARE_INT_RE.match(stripped):
            return False
        n = len(stripped)
        if n >= 4 and n % 2 == 0:
            half = n // 2
            return stripped[:half] == stripped[half:]
        # Odd length or shorter than 4 — not a doubled number
        return False
    return False


def _extract_printed_page(
    lines: List[str], pdf_page_num: int, front_matter_pages: int = FRONT_MATTER_PAGES
) -> int:
    """
    Extract the human-readable (printed) page number from the page content.

    Strategy
    --------
    Examine the last non-empty line.  If it is a bare integer, use that value.
    Otherwise fall back to ``pdf_page_num - front_matter_pages`` (minimum 1).

    Parameters
    ----------
    lines : list[str]
        Splitlines of the page text.
    pdf_page_num : int
        1-based PDF page index (used as fallback basis).
    front_matter_pages : int
        How many leading pages are front matter in this document.  Passed from
        the ``Chunker`` instance so the fallback is correct per doc_type.
    """
    for line in reversed(lines):
        stripped = line.strip()
        if stripped:
            if _BARE_INT_RE.match(stripped):
                return int(stripped)
            break  # last non-empty line is not a page number
    return max(1, pdf_page_num - front_matter_pages)


# ── Material-procedure title extraction ──────────────────────────────────────

def _find_mp_title(pages: List[Dict[str, Any]]) -> str:
    """
    Scan *pages* for the document title of an NJDOT material-procedure file.

    Strategy
    --------
    Iterate every line of every page and return the first line that:

    * matches ``_ALL_CAPS_TITLE_RE``  (all upper-case letters + punctuation)
    * has **≥ 4 words**               (excludes short header tokens such as
                                        "BUREAU OF MATERIALS" which is 3 words)
    * contains **no digit**           (excludes lines like "MP1-25" or codes)
    * contains **no colon**           (excludes KEYWORD: label lines such as
                                        "PURPOSE:" or "REFERENCES:")

    Falls back to ``"UNKNOWN MATERIAL PROCEDURE"`` if no line matches.
    """
    for page in pages:
        for raw_line in page.get("text", "").splitlines():
            stripped = raw_line.strip()
            if (
                stripped
                and _ALL_CAPS_TITLE_RE.match(stripped)
                and len(stripped.split()) >= 4
                and ":" not in stripped
                and not any(ch.isdigit() for ch in stripped)
            ):
                return stripped
    return "UNKNOWN MATERIAL PROCEDURE"


# ── Main class ────────────────────────────────────────────────────────────────

class Chunker:
    """
    Convert a list of page dicts (from ``PDFParser``) into chunk dicts.

    Parameters
    ----------
    doc_type : str
        ``"specs"`` (default), ``"scheduling"``, or ``"material_proc"``.
        Sets the default values of ``front_matter_pages``, ``index_tail_pages``,
        and the boundary heading level.  Individual overrides below take
        precedence.
    doc_name : str
        Document identifier used as ``section_id`` for ``material_proc`` files
        (e.g. ``"MP1-25"``).  Ignored for other doc types.
    max_tokens : int
        Hard token ceiling for a single chunk (default 750).
    overlap_tokens : int
        Number of tokens to repeat at the start of each continuation chunk
        when splitting an over-length section (default 100).
    front_matter_pages : int or None
        Number of leading PDF pages to skip.  ``None`` → use doc_type default
        (34 for "specs", 2 for "scheduling", 0 for "material_proc").
    index_tail_pages : int or None
        Number of trailing PDF pages to skip as the index.  ``None`` → use
        doc_type default (30 for "specs", 0 for others).
    """

    def __init__(
        self,
        doc_type:           str           = "specs",
        doc_name:           str           = "",
        max_tokens:         int           = MAX_TOKENS,
        overlap_tokens:     int           = OVERLAP_TOKENS,
        front_matter_pages: Optional[int] = None,
        index_tail_pages:   Optional[int] = None,
    ) -> None:
        if doc_type not in _DOC_PROFILES:
            raise ValueError(
                f"doc_type must be one of {list(_DOC_PROFILES)}; got {doc_type!r}"
            )
        profile = _DOC_PROFILES[doc_type]

        self.doc_type           = doc_type
        self.doc_name           = doc_name
        self.max_tokens         = max_tokens
        self.overlap_tokens     = overlap_tokens
        self.front_matter_pages = (
            front_matter_pages
            if front_matter_pages is not None
            else profile["front_matter_pages"]
        )
        self.index_tail_pages   = (
            index_tail_pages
            if index_tail_pages is not None
            else profile["index_tail_pages"]
        )
        # frozenset of detect() level names that open a new chunk.
        # Empty frozenset → whole document treated as a single block (material_proc).
        self._boundary_levels: frozenset[str] = profile["boundary_levels"]
        self._enc                             = _get_encoder()

    # ── Public entry point ────────────────────────────────────────────────────

    def chunk(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main entry point.

        Parameters
        ----------
        pages : list[dict]
            Output of ``PDFParser.extract_text()``.  Each dict must contain at
            minimum ``page_num`` (int, 1-based) and ``text`` (str).

        Returns
        -------
        list[dict]
            Each element has ``content`` (str) and ``metadata`` (dict).
        """
        total_pages = len(pages)
        valid_pages = self._filter_pages(pages, total_pages)

        # material_proc: treat the entire document as a single section block
        if not self._boundary_levels:
            block = self._build_single_doc_block(valid_pages)
            section_blocks = [block] if block is not None else []
        else:
            section_blocks = self._build_section_blocks(valid_pages)

        chunks: List[Dict[str, Any]] = []
        for block in section_blocks:
            chunks.extend(self._split_block(block))
        return chunks

    # ── Phase 1: page filtering ───────────────────────────────────────────────

    def _filter_pages(
        self, pages: List[Dict[str, Any]], total_pages: int
    ) -> List[Dict[str, Any]]:
        """Apply all page-level skip rules; return only processable pages."""
        index_cutoff = total_pages - self.index_tail_pages
        valid: List[Dict[str, Any]] = []

        for page in pages:
            pdf_num: int = page["page_num"]
            text: str   = page.get("text", "")

            # Rule 1: front matter
            if pdf_num <= self.front_matter_pages:
                continue

            # Rule 2: index section
            if pdf_num > index_cutoff:
                continue

            # Rule 3: blank pages
            if _is_blank(text):
                continue

            # Rule 4: TOC doubled-page-number artifact
            lines = text.splitlines()
            if _is_doubled_page_num(lines):
                continue

            valid.append(page)

        return valid

    # ── Phase 2: section block assembly ──────────────────────────────────────

    def _build_section_blocks(
        self, pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Walk filtered pages line-by-line and group text into section blocks.

        Boundary behaviour is driven by ``self._boundary_levels`` (set from
        ``doc_type`` in ``__init__``):

        ``"specs"`` mode  (boundaries = {"subsection", "sub_subsection"})
          - DIVISION headings: update ``current_division`` tracker; no new
            block opened; line is NOT added to current block content.
          - SECTION headings: flush any open block; update ``current_section``
            tracker; no new block opened.  Content between a SECTION heading
            and the first subsequent subsection is discarded.
          - SUBSECTION (XXX.XX) / SUB_SUBSECTION (XXX.XX.YY): flush current
            block and open a new one.
          - All other headings: accumulated as content in the current block.

        ``"scheduling"`` mode  (boundaries = {"decimal_section"})
          - Every ``decimal_section`` heading opens a new block.
          - All other headings (including any stray section / division lines)
            are accumulated as content.
          - No division tracker applies (``division`` is always ``""``).

        Content appearing before the very first boundary heading is discarded.

        Returns a list of intermediate block dicts:
            section_id, section_title, division,
            page_pdf, page_printed,
            lines: list[str]
        """
        blocks:           List[Dict[str, Any]] = []
        current_block:    Optional[Dict[str, Any]] = None
        current_division: str = ""

        for page in pages:
            pdf_num: int  = page["page_num"]
            text: str     = page.get("text", "")
            lines         = text.splitlines()
            printed_page  = _extract_printed_page(lines, pdf_num, self.front_matter_pages)

            for raw_line in lines:
                line = raw_line.strip()

                # Preserve blank lines inside a block (paragraph breaks)
                if not line:
                    if current_block is not None:
                        current_block["lines"].append("")
                    continue

                match = detect(line)

                # ── Plain content ─────────────────────────────────────────
                if match is None:
                    if current_block is not None:
                        current_block["lines"].append(line)
                    # Content before the first boundary heading is discarded
                    continue

                level = match["level"]

                # ── DIVISION (specs only): update tracker; no block action ─
                if level == "division" and self.doc_type == "specs":
                    current_division = match["title"]
                    # Do NOT add to current block; do NOT open a new block.

                # ── SECTION (specs only): flush open block; update tracker ─
                elif level == "section" and self.doc_type == "specs":
                    if current_block is not None:
                        blocks.append(current_block)
                        current_block = None
                    # Do NOT open a new block; wait for first subsection.

                # ── Primary boundary: flush current block, open a new one ─
                elif level in self._boundary_levels:
                    if current_block is not None:
                        blocks.append(current_block)

                    header_line = f'{match["section_id"]} {match["title"]}'
                    current_block = {
                        "section_id":    match["section_id"],
                        "section_title": match["title"],
                        "division":      current_division,
                        "page_pdf":      pdf_num,
                        "page_printed":  printed_page,
                        # First line is always "section_id section_title"
                        "lines":         [header_line],
                    }

                # ── Any other recognised heading: accumulate into block ────
                else:
                    if current_block is not None:
                        current_block["lines"].append(line)

        # Flush the final open block
        if current_block is not None:
            blocks.append(current_block)

        return blocks

    # ── Phase 2b: single-block assembly (material_proc) ──────────────────────

    def _build_single_doc_block(
        self, valid_pages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Collect ALL valid-page text into a single section block.

        Used when ``self._boundary_levels`` is empty (i.e. ``doc_type="material_proc"``).

        Returns
        -------
        dict or None
            A block dict with the standard keys (``section_id``, ``section_title``,
            ``division``, ``page_pdf``, ``page_printed``, ``lines``), or ``None`` if
            *valid_pages* is empty.
        """
        if not valid_pages:
            return None

        section_id    = self.doc_name or "UNKNOWN"
        section_title = _find_mp_title(valid_pages)
        header_line   = f"{section_id} {section_title}"

        first_page     = valid_pages[0]
        first_pdf_page = first_page["page_num"]
        first_lines    = first_page.get("text", "").splitlines()
        first_printed  = _extract_printed_page(
            first_lines, first_pdf_page, self.front_matter_pages
        )

        # Accumulate all lines from all pages; insert blank separator between pages.
        content_lines: List[str] = [header_line]
        for page in valid_pages:
            for raw_line in page.get("text", "").splitlines():
                content_lines.append(raw_line.strip())
            content_lines.append("")  # blank line between pages

        return {
            "section_id":    section_id,
            "section_title": section_title,
            "division":      "MATERIAL PROCEDURES",
            "page_pdf":      first_pdf_page,
            "page_printed":  first_printed,
            "lines":         content_lines,
        }

    # ── Phase 3: token-aware splitting ───────────────────────────────────────

    def _split_block(self, block: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a section block into one or more chunks of at most
        ``max_tokens`` tokens.

        * The **first** chunk uses the full ``max_tokens`` budget; it already
          contains ``"section_id  section_title"`` as its first line.
        * **Continuation** chunks have the section header prepended and use a
          budget of ``max_tokens - len(header_tokens)`` for the overlap + body.
        * Each continuation chunk begins with ``overlap_tokens`` tokens of
          context carried over from the end of the previous chunk.
        """
        text   = "\n".join(block["lines"]).strip()
        tokens = self._enc.encode(text)

        # Fits in a single chunk — fast path
        if len(tokens) <= self.max_tokens:
            return [self._make_chunk(block, text)]

        # Pre-compute the header cost for continuation chunks
        header_line   = f'{block["section_id"]} {block["section_title"]}'
        header_tokens = self._enc.encode(header_line + "\n")
        n_header      = len(header_tokens)
        cont_budget   = self.max_tokens - n_header  # tokens available for content

        chunks: List[Dict[str, Any]] = []
        start   = 0
        is_first = True

        while start < len(tokens):
            if is_first:
                # Header already embedded in the block text
                end        = min(start + self.max_tokens, len(tokens))
                chunk_text = self._enc.decode(tokens[start:end])
            else:
                # Prepend header; overlap text follows immediately after it
                end          = min(start + cont_budget, len(tokens))
                overlap_body = self._enc.decode(tokens[start:end])
                chunk_text   = header_line + "\n" + overlap_body

            chunks.append(self._make_chunk(block, chunk_text))

            if end >= len(tokens):
                break

            # Slide window: next chunk overlaps by OVERLAP_TOKENS tokens
            start    = end - self.overlap_tokens
            is_first = False

        return chunks

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _make_chunk(block: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Assemble the final chunk dict from a block and its resolved content."""
        return {
            "content": content,
            "metadata": {
                "section_id":    block["section_id"],
                "section_title": block["section_title"],
                "division":      block["division"],
                "page_pdf":      block["page_pdf"],
                "page_printed":  block["page_printed"],
                "kind":          "text",
            },
        }

    def count_tokens(self, text: str) -> int:
        """Return the token count for *text* using the configured encoding."""
        return len(self._enc.encode(text))


# ── Convenience wrapper ───────────────────────────────────────────────────────

def chunk_pages(
    pages:    List[Dict[str, Any]],
    doc_type: str = "specs",
    doc_name: str = "",
) -> List[Dict[str, Any]]:
    """
    One-shot helper: instantiate ``Chunker`` and chunk *pages* in a single call.

    Parameters
    ----------
    pages : list[dict]
        Output of ``PDFParser.extract_text()``.
    doc_type : str
        ``"specs"`` (default), ``"scheduling"``, or ``"material_proc"``.
    doc_name : str
        Document identifier (used as ``section_id`` for ``material_proc`` files).

    Returns
    -------
    list[dict]
        Chunk dicts with ``content`` and ``metadata``.
    """
    return Chunker(doc_type=doc_type, doc_name=doc_name).chunk(pages)


# ── Quick smoke test ──────────────────────────────────────────────────────────
# Run from the backend/ directory:
#
#     python -m app.ingestion.chunker
#
# Runs against both PDFs and prints:
#   • Total chunks for each document
#   • First 3 chunks of the scheduling manual with full metadata

if __name__ == "__main__":
    # Support running as a plain script as well as with -m
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from app.ingestion.pdf_parser import PDFParser  # noqa: E402

    enc = _get_encoder()

    # (pdf_filename, doc_type, print_first_3_chunks)
    _RUNS: list[tuple[str, str, bool]] = [
        ("StandSpecRoadBridge.pdf",          "specs",      False),
        ("constructionschedulingmanual.pdf", "scheduling", True),
    ]

    print("\n🧪 Chunker smoke test")
    print("=" * 70)

    for _pdf_name, _doc_type, _print_chunks in _RUNS:
        _pdf_path = _root / "data" / "raw_pdfs" / _pdf_name
        if not _pdf_path.exists():
            print(f"\n⚠️  {_pdf_name} not found — skipping.\n")
            continue

        print(f"\n📄 {_pdf_name}  [doc_type={_doc_type!r}]")
        _pages  = PDFParser(str(_pdf_path)).extract_text()
        _chunks = Chunker(doc_type=_doc_type).chunk(_pages)
        print(f"   PDF pages : {len(_pages)}")
        print(f"   Chunks    : {len(_chunks)}")

        if not _print_chunks:
            continue

        # ── First 3 chunks of the scheduling manual ───────────────────────
        if not _chunks:
            print("   ⚠️  No chunks produced.")
            continue

        print()
        for _i, _chunk in enumerate(_chunks[:3], start=1):
            _meta    = _chunk["metadata"]
            _content = _chunk["content"]
            _n_toks  = len(enc.encode(_content))
            _preview = " ".join(_content[:400].split())

            print("─" * 70)
            print(f"  Chunk {_i} of {len(_chunks)}")
            print(f"  section_id    : {_meta['section_id']}")
            print(f"  section_title : {_meta['section_title']}")
            print(f"  division      : {_meta['division']!r}")
            print(f"  page_pdf      : {_meta['page_pdf']}")
            print(f"  page_printed  : {_meta['page_printed']}")
            print(f"  kind          : {_meta['kind']}")
            print(f"  tokens        : {_n_toks} / {MAX_TOKENS}")
            print(f"  chars         : {len(_content)}")
            print(f"  content preview:")
            print(f"    {_preview[:300]!r}")

    print("\n" + "=" * 70)
    print("✅ Smoke test complete.\n")
