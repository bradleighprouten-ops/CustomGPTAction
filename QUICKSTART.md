# Quick Start Guide

## Prerequisites Setup

### 1. PostgreSQL Database
```powershell
# Ensure PostgreSQL is running and create database
# If password authentication fails, you may need to update .env with correct credentials
psql -U postgres
CREATE DATABASE ragdb;
\q
```

**Note**: If you get "password authentication failed", update the `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/ragdb
```
Replace `YOUR_PASSWORD` with your actual PostgreSQL password.

### 2. Qdrant Vector Database
```powershell
# Start Qdrant using Docker
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

Or download standalone: https://github.com/qdrant/qdrant/releases

### 3. Verify .env File
Ensure `E:\APP\.env` contains all required keys (already configured)

## Installation

### Option 1: Automated Setup (Recommended)
```powershell
cd E:\APP
.\setup.bat
```

### Option 2: Manual Setup
```powershell
cd E:\APP

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_setup.py

# Start application
python main.py
```

## Running the Application

### Start FastAPI Server
```powershell
cd E:\APP
python main.py
```

Or with uvicorn (with auto-reload):
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access Web Portal
Open browser: http://localhost:8000

### Upload Reports
1. Click "Choose File" and select a PDF report package
2. Select report type from dropdown
3. Click "Upload & Process"
4. Monitor status in dashboard (refreshes automatically)

## Custom GPT Setup

### Step 1: Create Custom GPT
1. Go to ChatGPT → Create → Custom GPT
2. Name: "Engineering Reports Assistant"
3. Add description and instructions from `CUSTOM_GPT_INSTRUCTIONS.md`

### Step 2: Configure Action
1. Go to Configure → Actions → Create new action
2. Import schema from `gpt_action_schema.json`
3. Or paste the JSON content directly

### Step 3: Add Authentication
- Authentication Type: **API Key**
- Auth Type: **Custom**
- Header Name: `X-API-Key`
- Value: `SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur`

### Step 4: Test Action
1. Use test query: "What causes building movement?"
2. Verify GPT calls the action
3. Check response includes report citations

## Testing the System

### Test API Directly
```powershell
# Using curl (if installed)
curl -X POST http://localhost:8000/api/query `
  -H "Content-Type: application/json" `
  -H "X-API-Key: SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur" `
  -d '{\"query\": \"building movement clay soil\", \"report_type\": \"building movement\"}'
```

Or use PowerShell:
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = "SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur"
}

$body = @{
    query = "building movement clay soil"
    report_type = "building movement"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Headers $headers -Body $body
```

### Check Health
```
http://localhost:8000/health
```

### View API Documentation
```
http://localhost:8000/docs
```

## Workflow

### 1. Upload Phase
```
User uploads PDF → FastAPI receives → Save to uploads/ → Create DB record → Queue background task
```

### 2. Processing Phase (Background)
```
Parse PDF (PyMuPDF) → Detect J-numbers → Chunk by section & paragraph → Embed (Voyage AI) → Index (Qdrant)
```

### 3. Query Phase
```
Custom GPT sends query → Embed query → Search Qdrant (6 results) → Rerank (top 3) → Return to GPT
```

## Troubleshooting

### Port Already in Use
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Database Connection Error
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure database `ragdb` exists

### Qdrant Connection Error
- Verify Qdrant is running: http://localhost:6333/dashboard
- Check QDRANT_URL in `.env`

### Embedding API Error
- Verify VOYAGE_API_KEY in `.env`
- Check API key has sufficient credits
- Test with smaller text samples first

### Upload Stuck in "Pending"
- Check console logs for errors
- Verify all services (PostgreSQL, Qdrant) are running
- Check upload_errors table for details

### No Search Results
- Ensure uploads show "success" status
- Verify Qdrant collection has vectors:
  ```
  http://localhost:6333/dashboard
  ```
- Try broader search terms

## File Locations

- **Application**: `E:\APP\`
- **Uploads**: `E:\APP\uploads\`
- **Logs**: Console output (can redirect to file)
- **Templates**: `E:\APP\templates\`
- **Config**: `E:\APP\.env`

## Useful Commands

### Check Upload Status
```powershell
# Via API
Invoke-RestMethod -Uri "http://localhost:8000/uploads"
```

### View Database Records
```sql
-- Connect to database
psql -U postgres -d ragdb

-- View uploads
SELECT * FROM uploads ORDER BY created_at DESC LIMIT 10;

-- View errors
SELECT u.file_name, e.stage, e.message 
FROM upload_errors e 
JOIN uploads u ON e.upload_id = u.id 
ORDER BY e.created_at DESC;
```

### Check Qdrant Collection
```
http://localhost:6333/dashboard
```
Or via API:
```
http://localhost:6333/collections/report-paragraphs
```

## Next Steps

1. Upload sample PDF reports through web portal
2. Verify processing completes successfully
3. Test queries via API
4. Set up Custom GPT with action
5. Test end-to-end workflow

## Support

For issues or questions:
- Check `README.md` for detailed documentation
- Review error logs in database
- Verify all prerequisites are running
- Test each component individually with `test_setup.py`
