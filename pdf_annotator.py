"""
PDF Annotation Service
Adds highlights and sticky notes to PDFs based on text spans
Uses RapidFuzz for fuzzy text matching
"""
import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz
import traceback


class TextSegment:
    """Represents where a paragraph appears on a specific page"""
    def __init__(self, page_num: int, start_char: int, end_char: int, text: str):
        self.page_num = page_num
        self.start_char = start_char
        self.end_char = end_char
        self.text = text


class PDFAnnotator:
    """Service for annotating PDFs with highlights and sticky notes"""
    
    def __init__(self):
        self.highlight_color = (1.0, 1.0, 0.0)  # Yellow RGB (0-1 scale)
        self.note_color = (1.0, 1.0, 0.0)  # Yellow RGB
    
    def find_text_on_pages(
        self,
        doc: fitz.Document,
        paragraph_text: str,
        page_hint: int,
        fuzzy_threshold: int = 80
    ) -> List[TextSegment]:
        """
        Find where paragraph text appears across pages starting from page_hint
        Uses fuzzy matching if exact match fails
        
        Returns list of TextSegment objects describing text location
        """
        segments = []
        
        # Try exact match first starting from page_hint
        for page_num in range(page_hint - 1, len(doc)):  # Convert to 0-indexed
            page = doc[page_num]
            page_text = page.get_text()
            
            # Try exact match
            if paragraph_text in page_text:
                start_idx = page_text.index(paragraph_text)
                segments.append(TextSegment(
                    page_num=page_num,
                    start_char=start_idx,
                    end_char=start_idx + len(paragraph_text),
                    text=paragraph_text
                ))
                return segments
        
        # Fallback to fuzzy matching
        best_match_page = None
        best_score = 0
        best_position = None
        
        for page_num in range(page_hint - 1, len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            # Use RapidFuzz to find best match
            score = fuzz.partial_ratio(paragraph_text, page_text)
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match_page = page_num
                
                # Find approximate position
                for i in range(len(page_text) - len(paragraph_text) + 1):
                    chunk = page_text[i:i + len(paragraph_text)]
                    chunk_score = fuzz.ratio(paragraph_text, chunk)
                    if chunk_score >= fuzzy_threshold:
                        best_position = i
                        break
        
        if best_match_page is not None and best_position is not None:
            segments.append(TextSegment(
                page_num=best_match_page,
                start_char=best_position,
                end_char=best_position + len(paragraph_text),
                text=paragraph_text
            ))
        
        return segments
    
    def char_spans_to_quads(
        self,
        page: fitz.Page,
        segment: TextSegment,
        spans: List[Tuple[int, int]]
    ) -> List[fitz.Quad]:
        """
        Convert character spans to line quads for highlighting
        
        Args:
            page: PyMuPDF page object
            segment: TextSegment describing where text is on page
            spans: List of (start, end) character positions relative to paragraph
        
        Returns:
            List of quads (4-point polygons) for highlighting
        """
        all_quads = []
        
        # Get all text instances with positions
        text_instances = page.get_text("words")  # Returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        
        # Build character-to-word mapping
        page_text = page.get_text()
        
        for span_start, span_end in spans:
            # Convert paragraph-relative positions to page-relative
            page_start = segment.start_char + span_start
            page_end = segment.start_char + span_end
            
            # Find words that intersect with this character range
            char_pos = 0
            for word_info in text_instances:
                x0, y0, x1, y1, word_text, *_ = word_info
                word_len = len(word_text)
                
                # Check if this word intersects with our span
                word_start = char_pos
                word_end = char_pos + word_len
                
                if word_end > page_start and word_start < page_end:
                    # This word is part of our highlight
                    rect = fitz.Rect(x0, y0, x1, y1)
                    quad = rect.quad
                    all_quads.append(quad)
                
                char_pos += word_len + 1  # +1 for space
        
        return all_quads
    
    def annotate_pdf(
        self,
        pdf_path: str,
        output_path: str,
        annotations: List[Dict]
    ) -> Dict:
        """
        Annotate PDF with highlights and sticky notes
        
        Args:
            pdf_path: Path to input PDF
            output_path: Path to save annotated PDF
            annotations: List of annotation dicts with:
                - paragraph_text: str (raw paragraph text)
                - spans: List[Tuple[int, int]] (character spans to highlight)
                - page_hint: int (starting page for search)
                - recommendation: str (sticky note content)
        
        Returns:
            Dict with success status and details
        """
        errors = []
        success_count = 0
        
        try:
            # Open PDF with error handling
            try:
                doc = fitz.open(pdf_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to open PDF: {str(e)}",
                    "traceback": traceback.format_exc()
                }
            
            # Validate PDF has pages
            if doc.page_count == 0:
                doc.close()
                return {
                    "success": False,
                    "error": "PDF has no pages"
                }
            
            for idx, annotation in enumerate(annotations):
                try:
                    paragraph_text = annotation["paragraph_text"]
                    spans = annotation["spans"]
                    page_hint = annotation["page_hint"]
                    recommendation = annotation["recommendation"]
                    
                    # Find where paragraph appears on pages
                    segments = self.find_text_on_pages(
                        doc=doc,
                        paragraph_text=paragraph_text,
                        page_hint=page_hint,
                        fuzzy_threshold=80
                    )
                    
                    if not segments:
                        # Add more diagnostic info
                        page_texts = []
                        for p_num in range(min(3, doc.page_count)):
                            page_texts.append(doc[p_num].get_text()[:200])
                        
                        errors.append({
                            "annotation_index": idx,
                            "error": "Text not found on any page",
                            "paragraph_preview": paragraph_text[:100],
                            "pdf_pages": doc.page_count,
                            "sample_text": page_texts[0] if page_texts else "No text extracted"
                        })
                        continue
                    
                    # Process each segment (usually just one)
                    for segment in segments:
                        page = doc[segment.page_num]
                        
                        # Convert character spans to quads
                        quads = self.char_spans_to_quads(page, segment, spans)
                        
                        if not quads:
                            errors.append({
                                "annotation_index": idx,
                                "page": segment.page_num + 1,
                                "error": "Could not map spans to word positions"
                            })
                            continue
                        
                        # Add highlight annotation
                        highlight = page.add_highlight_annot(quads)
                        highlight.set_colors(stroke=self.highlight_color)
                        highlight.set_opacity(0.5)
                        highlight.update()
                        
                        # Add sticky note at first quad position
                        first_quad = quads[0]
                        point = fitz.Point(first_quad.ul.x, first_quad.ul.y)
                        
                        note = page.add_text_annot(
                            point,
                            recommendation,
                            icon="Note"
                        )
                        note.set_colors(stroke=self.note_color)
                        note.update()
                        
                        success_count += 1
                
                except Exception as e:
                    errors.append({
                        "annotation_index": idx,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })
            
            # Save annotated PDF
            doc.save(output_path)
            doc.close()
            
            return {
                "success": True,
                "annotated_count": success_count,
                "error_count": len(errors),
                "errors": errors,
                "output_path": output_path
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }


# Singleton instance
pdf_annotator = PDFAnnotator()
