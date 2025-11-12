# Fixed Review Workflow - Upload ID Approach

## Problem Solved

**Root Cause**: Custom GPT cannot read uploaded PDF files and convert them to base64. When users upload a file to GPT, it only gets a file reference, not the actual content.

**Solution**: Use a two-step workflow where PDFs are uploaded to the web portal first, then referenced by ID in GPT actions.

## New Workflow

### Step 1: User Uploads PDF to Web Portal
```
User → Visits http://localhost:8001/
     → Uploads PDF with report type
     → Receives Upload ID (e.g., ID: 42)
```

### Step 2: User Tells GPT the Upload ID
```
User → "Please review upload #42"
```

### Step 3: GPT Extracts Paragraphs
```
GPT → Calls GET /review/extract-paragraphs/42
    → Receives discussion and conclusion paragraphs automatically
```

### Step 4: GPT Queries Similar Content  
```
GPT → Calls POST /review/query
    → Sends extracted paragraphs + report_type
    → Receives top 3 similar paragraphs for each
```

### Step 5: GPT Generates Recommendations
```
GPT → Analyzes matches
    → Creates specific recommendations
    → Identifies character spans to highlight
```

### Step 6: GPT Annotates PDF
```
GPT → Calls POST /review/annotate-by-id
    → Sends upload_id + annotations
    → Backend retrieves stored PDF
    → Returns annotated PDF in base64
```

### Step 7: GPT Returns Result
```
GPT → Converts base64 to downloadable file
    → Presents to user with summary
```

## New Endpoints

### GET `/review/extract-paragraphs/{upload_id}`
**Purpose**: Automatically extract paragraphs from uploaded PDF

**Parameters**:
- `upload_id` (path): The upload ID from web portal

**Returns**:
```json
{
  "success": true,
  "upload_id": 42,
  "file_name": "J250449-1.pdf",
  "report_type": "building movement",
  "discussion_paragraphs": [
    {"text": "...", "page": 6},
    {"text": "...", "page": 6}
  ],
  "conclusion_paragraphs": [
    {"text": "...", "page": 7}
  ]
}
```

### POST `/review/annotate-by-id`
**Purpose**: Annotate PDF by referencing its upload ID

**Request**:
```json
{
  "upload_id": 42,
  "annotations": [
    {
      "paragraph_text": "Full paragraph text...",
      "spans": [[0, 50], [100, 150]],
      "page_hint": 6,
      "recommendation": "Your recommendation..."
    }
  ]
}
```

**Returns**: Same as `/review/annotate` - annotated PDF in base64

## Updated Custom GPT Instructions

```
When user requests a review:

1. Ask user: "Please upload your PDF to the web portal at [URL] and tell me the Upload ID"
2. Once you have the upload ID, call extractParagraphsFromUpload
3. Review the extracted paragraphs
4. Call reviewQuery with the paragraphs and report_type
5. Analyze the matches and generate recommendations
6. Call reviewAnnotateById with upload_id and your annotations
7. Return the annotated PDF to the user

Example:
User: "Review my earthquake assessment report"
You: "Please upload your PDF to https://your-portal-url.com and share the Upload ID with me."
User: "Upload ID is 42"
You: [Call extractParagraphsFromUpload(42)]
     [Analyze paragraphs...]
     [Call reviewQuery with paragraphs]
     [Generate recommendations...]
     [Call reviewAnnotateById with annotations]
     "Here's your annotated report with recommendations..."
```

## Benefits

✅ **No base64 transfer issues** - PDF stays on server
✅ **Automatic paragraph extraction** - GPT doesn't need to parse PDF
✅ **Works with any PDF** - No corruption during transfer
✅ **Simpler for users** - Upload once, reference by ID
✅ **Better error handling** - Clear error messages with upload ID

## Testing

1. Upload a PDF via web portal (http://localhost:8001/)
2. Note the Upload ID
3. Test extraction: `GET /review/extract-paragraphs/{id}`
4. Test annotation: `POST /review/annotate-by-id` with upload_id

## Files Modified

- `main.py`: Added 2 new endpoints
- `gpt_action_schema.json`: Added endpoint schemas
- `CUSTOM_GPT_INSTRUCTIONS.md`: Updated with new workflow
