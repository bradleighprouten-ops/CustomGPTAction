# Review Workflow - Alternative Approach

## Problem Identified

Custom GPT **CANNOT** read uploaded PDF files and convert them to base64 to send via actions. When a user uploads a file to Custom GPT, the GPT only receives a file reference/ID, not the actual file content.

## Solution: Two-Step Workflow

### Option 1: Web Portal Upload (Recommended)

Instead of GPT handling the PDF annotation, use this workflow:

1. **User uploads PDF to GPT** → GPT extracts text/paragraphs (GPT can read PDF text)
2. **GPT calls /review/query** → Gets similar paragraphs  
3. **GPT generates recommendations** → Presents them to user
4. **User uploads original PDF to web portal** → Portal has direct file access
5. **Portal calls /review/annotate** → Returns annotated PDF

### Option 2: Multipart Upload Endpoint (Better)

Create a new endpoint that accepts PDF as multipart/form-data instead of base64:

```python
@app.post("/review/annotate-upload")
async def review_annotate_upload(
    pdf_file: UploadFile = File(...),
    annotations_json: str = Form(...),
    api_key: str = Depends(verify_api_key)
):
    # Accept PDF directly as file upload
    # Parse annotations from JSON string
    # Process and return annotated PDF
```

**But Custom GPT actions don't support multipart/form-data uploads!**

### Option 3: Separate Upload Step

1. User uploads PDF to web portal at `/upload-for-review`
2. Server stores PDF temporarily with UUID
3. Returns UUID to user
4. User gives UUID to GPT
5. GPT calls `/review/annotate` with UUID + annotations
6. Server retrieves stored PDF, annotates it, returns result

## Recommended Implementation

Since Custom GPT **cannot pass file contents via actions**, we should:

### Approach A: Manual Workflow
1. GPT provides recommendations as text
2. User manually applies them
3. Or user uses separate web interface for annotation

### Approach B: Hybrid Workflow (Best)
1. User uploads PDF to web portal
2. Portal generates upload ID
3. User tells GPT the upload ID
4. GPT extracts paragraphs by asking user or reading from portal
5. GPT calls /review/query with paragraphs
6. GPT calls /review/annotate-by-id with upload_id + annotations
7. Portal retrieves PDF, annotates, returns download link

## Updated Architecture Needed

```
[User] 
  ↓ uploads PDF
[Web Portal] → stores PDF → returns upload_id
  ↓ 
[User] → tells GPT: "Review upload #12345"
  ↓
[Custom GPT] → calls /review/query-by-id?upload_id=12345
  ↓ gets paragraphs automatically
[Custom GPT] → analyzes → generates recommendations
  ↓
[Custom GPT] → calls /review/annotate-by-id with upload_id + annotations
  ↓
[Backend] → retrieves stored PDF → annotates → returns download URL
  ↓
[User] downloads annotated PDF
```

This avoids the base64 transfer issue entirely!
