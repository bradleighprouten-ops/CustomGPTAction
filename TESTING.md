# Testing Instructions

## Before Testing

1. **Start PostgreSQL**
   - Ensure PostgreSQL is running
   - Database `ragdb` should exist

2. **Start Qdrant**
   ```powershell
   docker run -p 6333:6333 qdrant/qdrant
   ```

3. **Run System Tests**
   ```powershell
   cd E:\APP
   python test_setup.py
   ```

4. **Start Application**
   ```powershell
   python main.py
   ```

## Test Workflow

### Phase 1: Upload Test
1. Open browser: http://localhost:8000
2. Prepare a test PDF with:
   - J-numbers in footer (e.g., J250254-1)
   - Multiple reports in one PDF
   - Sections like "Introduction", "Discussion", etc.
3. Upload via web portal
4. Select appropriate report type
5. Monitor console output for processing logs

### Phase 2: Verify Processing
1. Check upload status in dashboard (refresh page)
2. If status = "success" ✅
   - Check console logs for paragraph count
   - Verify Qdrant: http://localhost:6333/dashboard
3. If status = "error" ❌
   - Run: `python manage.py errors <upload_id>`
   - Review error message and stack trace
   - Fix issue and retry

### Phase 3: API Testing

**Test Query Endpoint:**
```powershell
# PowerShell
$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = "SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur"
}

$body = @{
    query = "building movement"
    report_type = "building movement"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -Headers $headers -Body $body

$response | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
  "success": true,
  "query": "building movement",
  "results": [
    {
      "text": "Paragraph content...",
      "report_id": "J250254-1",
      "section": "Discussion",
      "report_type": "building movement",
      "page_number": 5,
      "similarity_score": 0.85,
      "relevance_score": 0.92
    }
  ],
  "count": 3
}
```

### Phase 4: Custom GPT Integration

1. **Create Custom GPT** (ChatGPT Plus required)
   - Go to ChatGPT → Explore GPTs → Create
   - Name: "Engineering Reports Assistant"
   - Copy instructions from `CUSTOM_GPT_INSTRUCTIONS.md`

2. **Add Action**
   - Configure → Actions → Create new action
   - Import schema from `gpt_action_schema.json`
   - Or paste JSON content directly
   - Server URL: `http://localhost:8000` (or your deployed URL)

3. **Configure Authentication**
   - Type: API Key
   - Auth Type: Custom
   - Header: `X-API-Key`
   - Value: `SK-6egfst476yshjfjGBfyte8ui46768t7ijghgr6e4576rur`

4. **Test with GPT**
   ```
   Test queries:
   - "What are common causes of building movement?"
   - "Find examples of retaining wall failures"
   - "Show me reports about foundation settlement"
   ```

5. **Verify Response**
   - GPT should call queryReports action
   - Check backend logs for API call
   - Response should cite report IDs (J-numbers)

## Troubleshooting

### Upload Processing Fails

**Check 1: Console Logs**
```
Look for error messages in console output
Common issues:
- PyMuPDF parsing errors
- Voyage AI API errors
- Qdrant connection errors
```

**Check 2: Database Errors**
```powershell
python manage.py errors <upload_id>
```

**Check 3: Test Individual Components**
```powershell
python test_setup.py
```

### No Search Results

**Problem**: Query returns empty results

**Solutions:**
1. Verify uploads are successful:
   ```powershell
   python manage.py list
   ```
2. Check Qdrant has vectors:
   ```powershell
   python manage.py check-qdrant
   ```
3. Try broader search terms
4. Check report_type filter matches uploaded data

### GPT Action Not Working

**Problem**: Custom GPT doesn't call action

**Solutions:**
1. Verify backend is running (http://localhost:8000/health)
2. Check API key in GPT configuration
3. Test endpoint directly with curl/PowerShell
4. Review GPT action schema syntax
5. Check server URL is accessible

### Processing Hangs

**Problem**: Upload stuck in "processing"

**Solutions:**
1. Check console for errors
2. Restart application
3. Reset status manually:
   ```powershell
   python manage.py reset-status <id> pending
   ```
4. Delete and re-upload:
   ```powershell
   python manage.py clear-failed
   ```

## Sample Test Data

### Create Test PDF

If you don't have real reports, create a test PDF with:

**Page 1:**
```
J250254-1

BUILDING MOVEMENT REPORT

Introduction
This report presents findings from the inspection of a residential property 
experiencing structural movement. The assessment focused on identifying 
causes and recommending appropriate remediation strategies.

Background
The property is a two-storey brick structure constructed in 1985 on 
reactive clay soils. The owner reported progressive cracking over the 
past 12 months.
```

**Page 2:**
```
Site Inspection
On site inspection, diagonal cracking was observed in the front facade 
brick masonry, extending from window corners. Internal walls showed 
minor hairline cracks. External ground levels appeared uneven near the 
foundation perimeter.

Discussion
The observed cracking pattern is consistent with differential settlement 
caused by moisture-related clay soil movement. Seasonal variations in 
soil moisture content lead to volumetric changes in reactive clay.

J250254-1
```

**Page 3:**
```
Recommendations
1. Monitor crack progression over 6-12 months
2. Improve surface drainage away from foundations
3. Consider underpinning if movement continues
4. Regular watering program during dry periods

Conclusion
The building shows signs of foundation movement related to reactive 
clay soil behavior. Recommended monitoring and drainage improvements.

J250254-1
```

### Upload Test PDF
1. Save above as PDF
2. Upload with report_type = "building movement"
3. Should parse into 1 report with 6 sections

## Validation Checklist

- [ ] System tests pass (test_setup.py)
- [ ] Application starts without errors
- [ ] Web portal loads (http://localhost:8000)
- [ ] Can upload PDF file
- [ ] Upload processes successfully (status = success)
- [ ] Qdrant shows vectors (check-qdrant)
- [ ] API query returns results
- [ ] Custom GPT action configured
- [ ] GPT successfully calls action
- [ ] Response includes report citations

## Performance Benchmarks

**Expected Processing Times:**
- Small PDF (1 report, 5 pages): ~30 seconds
- Medium PDF (5 reports, 25 pages): ~90 seconds
- Large PDF (20 reports, 100 pages): ~5 minutes

**Query Response:**
- API query: ~500-1000ms
- Includes: embedding + search + reranking

**Factors Affecting Speed:**
- PDF complexity (scanned vs digital)
- Number of paragraphs to embed
- Voyage AI API latency
- Network conditions

## Next Steps After Testing

1. **Test with Real Data**
   - Upload actual engineering reports
   - Verify chunking is accurate
   - Check J-number detection

2. **Refine Search**
   - Test various queries
   - Adjust retrieval counts if needed
   - Fine-tune section detection

3. **Custom GPT Optimization**
   - Refine instructions for better responses
   - Add example queries
   - Test edge cases

4. **Production Preparation**
   - Set up proper logging
   - Add monitoring
   - Configure backups
   - Deploy to server

## Management Commands Reference

```powershell
# List all uploads
python manage.py list

# Show errors for specific upload
python manage.py errors 5

# Show latest errors
python manage.py errors

# Delete failed uploads
python manage.py clear-failed

# Check Qdrant status
python manage.py check-qdrant

# Reset upload status
python manage.py reset-status 5 pending
```

## Useful Queries

**PostgreSQL:**
```sql
-- View all uploads
SELECT id, file_name, topic, status, created_at FROM uploads;

-- Count by status
SELECT status, COUNT(*) FROM uploads GROUP BY status;

-- Recent errors
SELECT u.file_name, e.stage, e.message 
FROM upload_errors e 
JOIN uploads u ON e.upload_id = u.id 
ORDER BY e.created_at DESC 
LIMIT 10;
```

**Qdrant Dashboard:**
```
http://localhost:6333/dashboard
```

## Support Resources

- `README.md` - Complete documentation
- `QUICKSTART.md` - Quick start guide
- `CUSTOM_GPT_INSTRUCTIONS.md` - GPT setup
- `E:\AGENT\RAG_Backend_Project_Notes.md` - Technical notes
- Console logs - Real-time debugging
- Database errors table - Detailed error tracking

## Success Criteria

✅ **System is working correctly when:**
1. Uploads process to "success" status
2. Qdrant collection shows correct vector count
3. API queries return relevant results
4. Results include proper metadata (report_id, section)
5. Rerank scores improve relevance
6. Custom GPT calls action successfully
7. GPT responses cite report sources

Good luck with testing! 🚀
