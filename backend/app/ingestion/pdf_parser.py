"""
PDF Parser for NJDOT Chatbot.
Extracts text from PDFs using pdfplumber (primary) and PyMuPDF (fallback).
"""

import pdfplumber
import fitz  # PyMuPDF
import argparse
from typing import Any, Dict, List
from pathlib import Path


class PDFParser:
    """Extract text from PDF files"""
    
    def __init__(self, pdf_path: str):
        """Initialize parser with PDF path"""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    def extract_text(self) -> List[Dict[str, Any]]:
        """
        Extract text from all pages
        
        Returns:
            List of dicts with page info:
            [
                {
                    "page_num": 1,
                    "text": "page content...",
                    "char_count": 1500
                },
                ...
            ]
        """
        print(f"Extracting text from: {self.pdf_path.name}")
        
        pages = []
        
        try:
            # Try pdfplumber first (primary extractor)
            pages = self._extract_with_pdfplumber()
            print(f"✅ Extracted {len(pages)} pages with pdfplumber")
            
        except Exception as e:
            print(f"⚠️  pdfplumber failed: {str(e)}")
            print("🔄 Falling back to PyMuPDF...")
            
            try:
                # Fallback to PyMuPDF
                pages = self._extract_with_pymupdf()
                print(f"Extracted {len(pages)} pages with PyMuPDF")
                
            except Exception as e2:
                print(f"❌ Both extractors failed!")
                print(f"   pdfplumber error: {str(e)}")
                print(f"   PyMuPDF error: {str(e2)}")
                raise
        
        return pages
    
    def _extract_with_pdfplumber(self) -> List[Dict[str, Any]]:
        """Extract text using pdfplumber"""
        pages = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                
                pages.append({
                    "page_num": i,
                    "text": text,
                    "char_count": len(text),
                    "extractor": "pdfplumber"
                })
        
        return pages
    
    def _extract_with_pymupdf(self) -> List[Dict[str, Any]]:
        """Extract text using PyMuPDF (fallback)"""
        pages = []
        
        doc = fitz.open(self.pdf_path)
        
        for i, page in enumerate(doc, start=1):
            text = page.get_text() or ""
            
            pages.append({
                "page_num": i,
                "text": text,
                "char_count": len(text),
                "extractor": "pymupdf"
            })
        
        doc.close()
        
        return pages
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get PDF metadata"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                return {
                    "filename": self.pdf_path.name,
                    "total_pages": len(pdf.pages),
                    "metadata": pdf.metadata or {}
                }
        except Exception as e:
            return {
                "filename": self.pdf_path.name,
                "error": str(e)
            }


def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Convenience function to extract text from PDF
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        List of page dictionaries
    """
    parser = PDFParser(pdf_path)
    return parser.extract_text()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from a PDF for quick testing.")
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=None,
        help="Optional path to PDF. If omitted, defaults to scheduling manual when available.",
    )
    parser.add_argument(
        "--preview-pages",
        type=int,
        default=3,
        help="How many pages to show in preview output.",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).parent.parent.parent / "data" / "raw_pdfs"

    if args.pdf_path:
        test_pdf = Path(args.pdf_path)
    else:
        preferred_names = [
            "construction scheduling manual.pdf",
            "ConstructionSchedulingManual.pdf",
            "constructionschedulingmanual.pdf",
        ]
        test_pdf = None
        for name in preferred_names:
            candidate = data_dir / name
            if candidate.exists():
                test_pdf = candidate
                break
        if test_pdf is None:
            pdf_files = sorted(data_dir.glob("*.pdf"))
            test_pdf = pdf_files[0] if pdf_files else None

    if test_pdf is None or not test_pdf.exists():
        raise FileNotFoundError(
            "No PDF found. Pass a path explicitly, e.g. backend/data/raw_pdfs/construction scheduling manual.pdf"
        )

    print(f"\n🧪 Testing PDF parser on: {test_pdf.name}")
    print("=" * 60)

    parser_instance = PDFParser(str(test_pdf))
    metadata = parser_instance.get_metadata()
    print("\n📋 Metadata:")
    print(f"   Filename: {metadata['filename']}")
    print(f"   Total pages: {metadata.get('total_pages', 'unknown')}")

    pages = parser_instance.extract_text()
    print("\n📄 Extraction Results:")
    print(f"   Total pages extracted: {len(pages)}")
    print("\n📊 Sample Pages:")
    for page in pages[: max(0, args.preview_pages)]:
        print(
            f"   Page {page['page_num']}: {page['char_count']} chars ({page['extractor']})"
        )
    if pages and pages[0]["text"]:
        snippet = pages[0]["text"][:200].replace("\n", " ")
        print("\n📝 First page snippet:")
        print(f"   {snippet}...")
    print("\n✅ PDF parsing successful!")
