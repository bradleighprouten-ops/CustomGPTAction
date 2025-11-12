# RAG Backend Application

Engineering Reports RAG (Retrieval-Augmented Generation) system with Custom GPT integration.

## Features

- 📄 PDF report parsing with regex-based J-number detection
- 🧩 Intelligent chunking by report, section, and paragraph
- 🔍 Vector search with voyage-3-large embeddings
- 🎯 Reranking with rerank-2.5-lite for improved relevance
- 💾 PostgreSQL for upload tracking and error logging
- 🗂️ Qdrant vector database for semantic search
- 🌐 Web portal for PDF uploads
- 🤖 Custom GPT action endpoint

## Architecture

```
User Upload → FastAPI → Background Processing:
                         1. PyMuPDF (Parse & Chunk)
                         2. Voyage AI (Embed)
                         3. Qdrant (Index)
                         
Custom GPT → /api/query → Embed Query → Qdrant (6 results) → Rerank (Top 3) → Response
```

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL database running on localhost:5432
- Qdrant running on localhost:6333
- API keys in `.env` file

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL database `ragdb` exists:
```sql
CREATE DATABASE ragdb;
```

3. Ensure Qdrant is running:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

4. Run the application:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Usage

### Web Portal

Access at `http://localhost:8000`

1. Upload PDF report packages
2. Select report type (building movement, retaining wall, etc.)
3. Monitor processing status
4. View upload history and errors

### Custom GPT Integration

#### Setup Custom GPT Action

1. Go to ChatGPT → Create Custom GPT
2. Configure → Actions → Import from URL or paste schema
3. Use `gpt_action_schema.json` content
4. Set authentication:
   - Type: API Key
   - Header name: `X-API-Key`
   - Value: ``

#### Example GPT Prompt

```
You are an engineering assistant with access to a database of structural engineering reports.

When users ask questions about:
- Building movement
- Retaining walls
- Foundation issues
- Structural assessments

Use the queryReports action to retrieve relevant report excerpts, then answer based on that context.

Always cite the report ID (J-number) and section when referencing information.
```

#### API Request Example

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur" \
  -d '{
    "query": "What causes building movement in clay soils?",
    "report_type": "building movement"
  }'
```

#### API Response Example

```json
{
  "success": true,
  "query": "What causes building movement in clay soils?",
  "results": [
    {
      "text": "Clay soils are particularly susceptible to volumetric changes...",
      "report_id": "J250254-1",
      "section": "Discussion",
      "report_type": "building movement",
      "page_number": 5,
      "similarity_score": 0.87,
      "relevance_score": 0.94
    }
  ],
  "count": 3
}
```

## Project Structure

```
E:\APP\
├── main.py                    # FastAPI application
├── config.py                  # Configuration management
├── database.py                # PostgreSQL models & connection
├── pdf_processor.py           # PDF parsing & chunking
├── embeddings.py              # Voyage AI embedding service
├── qdrant_client.py           # Qdrant vector DB operations
├── reranker.py                # Voyage AI reranking service
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (API keys)
├── gpt_action_schema.json     # OpenAI custom action schema
├── templates/
│   └── index.html            # Web portal template
├── static/
│   └── styles.css            # Custom styles (optional)
└── uploads/                   # Uploaded PDF storage
```

## Database Schema

### Upload Table
- `id`: Primary key
- `file_name`: Original PDF filename
- `topic`: Report type category
- `status`: pending | processing | success | error
- `created_at`, `updated_at`: Timestamps

### UploadError Table
- `id`: Primary key
- `upload_id`: Foreign key to Upload
- `stage`: parsing | embedding | qdrant
- `message`: Error message
- `details`: Stack trace / additional info
- `created_at`: Timestamp

## Processing Pipeline

### 1. PDF Parsing
- Detect report boundaries by J-number regex (J######-#)
- First page: scan full body
- Subsequent pages: scan footer
- Split when J-number changes

### 2. Chunking
- Chunk by sections: Introduction, Background, Site Inspection, Discussion, Recommendation, Conclusion
- Further chunk by paragraphs (>50 chars)
- Attach metadata: report_id, section, report_type, page_number

### 3. Embedding
- Batch embed paragraphs with voyage-3-large
- 1024-dimensional vectors
- Input type: "document"

### 4. Indexing
- Store in Qdrant collection: `report-paragraphs`
- Cosine similarity distance metric
- Metadata preserved in payload

### 5. Search & Retrieval
- Embed query with input_type: "query"
- Retrieve 6 initial results (cosine similarity)
- Rerank with rerank-2.5-lite → top 3
- Return with both similarity and relevance scores

## Error Handling

- All processing errors logged to `upload_errors` table
- Errors tracked by stage: parsing, embedding, qdrant
- Stack traces stored in `details` field
- Upload status updated to "error" on failure

## Maintenance

### Clear Qdrant Collection
```python
from qdrant_client import qdrant_service
qdrant_service.client.delete_collection("report-paragraphs")
qdrant_service._ensure_collection()  # Recreate
```

### Database Migrations
```bash
# If using Alembic (optional)
alembic init migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Troubleshooting

**Issue**: Database password authentication failed
- Update `DATABASE_URL` in `.env` with your PostgreSQL password:
  ```
  DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/ragdb
  ```
- Or check if PostgreSQL is configured to allow local connections without password (pg_hba.conf)

**Issue**: Upload stuck in "pending"
- Check console logs for errors
- Verify Qdrant is running
- Check API keys in `.env`

**Issue**: No search results
- Verify reports were processed successfully (status = "success")
- Check Qdrant collection has vectors
- Try broader search queries

**Issue**: Authentication error from GPT
- Verify X-API-Key header matches `.env` APP_API_KEY
- Check Custom GPT action authentication settings

## Notes for Next Agent

- Upload processing is fully async via FastAPI BackgroundTasks
- Each upload creates a new DB session to avoid conflicts
- Embeddings are batched for efficiency
- Reranking requires original documents, not just vectors
- Custom GPT should cite report_id (J-number) in responses
- Consider adding retry logic for failed embeddings
- May want to add file size validation before upload
- Consider pagination for large upload lists

## Performance Optimization

- Batch embedding: Process multiple paragraphs at once
- Background processing: Non-blocking uploads
- Connection pooling: AsyncPG for database
- Vector search: Optimized with Qdrant's HNSW index

## Future Enhancements

- [ ] Add report preview/viewer
- [ ] Implement delete functionality
- [ ] Add batch upload support
- [ ] Export search results
- [ ] Analytics dashboard
- [ ] Rate limiting on API endpoint
- [ ] Webhook notifications on processing completion
