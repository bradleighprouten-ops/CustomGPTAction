"""
PDF Processing Module
Uses PyMuPDF to parse PDFs, detect reports by J-number regex,
chunk by sections and paragraphs
"""
import re
import fitz  # PyMuPDF
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Paragraph:
    """Represents a single paragraph chunk with metadata"""
    text: str
    report_id: str
    section: str
    report_type: str
    page_number: int


@dataclass
class Report:
    """Represents a single report with its paragraphs"""
    report_id: str
    paragraphs: List[Paragraph]


# Regex pattern for J-number detection (e.g., J250254-1, J123456-2)
J_NUMBER_PATTERN = re.compile(r'\bJ\d{6}-\d+\b')

# Section headers to detect
SECTIONS = [
    "introduction",
    "background",
    "site inspection",
    "discussion",
    "recommendation",
    "recommendations",
    "conclusion",
    "conclusions"
]


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, any]]:
    """
    Extract text from PDF with page numbers
    Returns list of dicts with page_num and text
    """
    doc = fitz.open(pdf_path)
    pages = []
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        pages.append({
            "page_num": page_num,
            "text": text
        })
    
    doc.close()
    return pages


def detect_j_numbers(text: str) -> List[str]:
    """Extract all J-numbers from text"""
    matches = J_NUMBER_PATTERN.findall(text)
    return list(set(matches))  # Remove duplicates


def split_into_reports(pages: List[Dict[str, any]]) -> Dict[str, List[Dict[str, any]]]:
    """
    Split pages into individual reports based on J-number detection
    First page: detect in body
    Subsequent pages: detect in footer (last 200 chars)
    """
    reports = {}
    current_j_number = None
    
    for page in pages:
        page_num = page["page_num"]
        text = page["text"]
        
        # First page or when J-number changes: check full body
        j_numbers_body = detect_j_numbers(text[:1000])  # Check first 1000 chars
        
        # Check footer (last 200 chars) for subsequent pages
        j_numbers_footer = detect_j_numbers(text[-200:])
        
        # Determine active J-number
        if j_numbers_body:
            # New report detected
            current_j_number = j_numbers_body[0]
        elif j_numbers_footer:
            # Continuation with footer J-number
            detected = j_numbers_footer[0]
            if detected != current_j_number:
                # J-number changed
                current_j_number = detected
        
        # Add page to current report
        if current_j_number:
            if current_j_number not in reports:
                reports[current_j_number] = []
            reports[current_j_number].append(page)
    
    return reports


def detect_section(text: str) -> str:
    """
    Detect section from text by looking for section headers
    Returns section name or 'other' if not found
    """
    text_lower = text.lower()
    
    for section in SECTIONS:
        if section in text_lower:
            # Return standardized section name
            if "introduction" in section:
                return "Introduction"
            elif "background" in section:
                return "Background"
            elif "site inspection" in section:
                return "Site Inspection"
            elif "discussion" in section:
                return "Discussion"
            elif "recommendation" in section:
                return "Recommendation"
            elif "conclusion" in section:
                return "Conclusion"
    
    return "Other"


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs
    Paragraphs are separated by double newlines or significant whitespace
    """
    # Split by double newlines
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Clean and filter
    cleaned = []
    for para in paragraphs:
        para = para.strip()
        # Only keep paragraphs with substantial content (>50 chars)
        if len(para) > 50:
            cleaned.append(para)
    
    return cleaned


def chunk_report(report_pages: List[Dict[str, any]], report_id: str, report_type: str) -> List[Paragraph]:
    """
    Chunk a single report into paragraphs with metadata
    Groups pages, detects sections, splits into paragraphs
    """
    paragraphs = []
    
    # Combine all pages for this report
    full_text = "\n\n".join([page["text"] for page in report_pages])
    
    # Simple section detection: split by section headers
    current_section = "Other"
    
    for page in report_pages:
        page_text = page["text"]
        page_num = page["page_num"]
        
        # Detect if this page starts a new section
        detected_section = detect_section(page_text[:500])  # Check first 500 chars
        if detected_section != "Other":
            current_section = detected_section
        
        # Split page into paragraphs
        page_paragraphs = split_into_paragraphs(page_text)
        
        for para_text in page_paragraphs:
            # Re-detect section for this specific paragraph if header present
            para_section = detect_section(para_text[:200])
            if para_section != "Other":
                current_section = para_section
            
            paragraph = Paragraph(
                text=para_text,
                report_id=report_id,
                section=current_section,
                report_type=report_type,
                page_number=page_num
            )
            paragraphs.append(paragraph)
    
    return paragraphs


def process_pdf(pdf_path: str, report_type: str) -> List[Paragraph]:
    """
    Main function to process a PDF file
    Returns list of all paragraphs from all reports with metadata
    """
    # Step 1: Extract pages
    pages = extract_text_from_pdf(pdf_path)
    
    # Step 2: Split into reports by J-number
    reports = split_into_reports(pages)
    
    # Step 3: Chunk each report into paragraphs
    all_paragraphs = []
    for report_id, report_pages in reports.items():
        paragraphs = chunk_report(report_pages, report_id, report_type)
        all_paragraphs.extend(paragraphs)
    
    return all_paragraphs
