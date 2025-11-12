# Review Endpoint Troubleshooting Guide

## Issue Identified
The `/review/annotate` endpoint is receiving corrupted or improperly encoded PDF files from Custom GPT.

## Root Cause
When Custom GPT uploads a PDF and tries to send it via the action, the file may be:
1. Partially corrupted during transfer
2. Incorrectly base64 encoded
3. A scanned image PDF (not text-based)
4. Flattened or encrypted

## Solution

### For the Custom GPT Instructions:
Add this to your Custom GPT instructions:

```
IMPORTANT: When using the review/annotate action:

1. **PDF Requirements**:
   - Must be a text-based PDF (not scanned images)
   - Must be exported directly from Word, Google Docs, or PDF software
   - Should NOT be flattened, encrypted, or password-protected
   - File size should be reasonable (< 10MB recommended)

2. **If annotation fails**:
   - Ask the user to re-upload the ORIGINAL PDF file
   - Verify the PDF can be opened and text can be selected/copied
   - Try with a simpler test PDF first to verify connectivity
   
3. **Error handling**:
   - If you receive "Invalid or corrupted PDF" error, inform the user:
     "The PDF appears to be corrupted or is not a text-based PDF. 
      Please export a fresh copy directly from your document editor (Word, Google Docs, etc.)
      and upload that version."
```

### For API Improvements:
The following improvements have been added to `main.py`:

1. **PDF Validation**: Before processing, the endpoint now validates that:
   - Base64 decoding succeeds
   - The decoded bytes can be opened as a valid PDF
   - The PDF has pages with extractable text

2. **Better Error Messages**: Returns specific error messages:
   - "Invalid base64 encoding" - the base64 string is malformed
   - "Invalid or corrupted PDF file" - the PDF cannot be opened
   - Includes instructions to upload non-scanned PDF

3. **Diagnostic Information**: When text matching fails, includes:
   - Number of pages in PDF
   - Sample text from first page
   - Paragraph preview that couldn't be matched

## Testing

Test the fix by running:
```bash
cd E:\APP
python diagnose_pdf.py
```

This will create a test PDF and verify encoding/decoding works.

## Next Steps

1. Restart the server with the updated code
2. Update Custom GPT instructions with PDF requirements
3. Test with a known-good PDF (exported directly from Word)
4. If issues persist, use `diagnose_pdf.py` to test the specific base64 string

## Common Issues & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid base64 encoding" | Malformed base64 string | Ensure GPT is sending complete base64 without corruption |
| "Invalid or corrupted PDF" | File is scanned/flattened | Upload original non-scanned PDF |
| "Text not found on any page" | OCR needed or wrong page | Check page_hint, ensure PDF has text layer |
| Connection refused | Server not running | Start server: `python main.py` |
