"""
FastAPI Main Application
Handles file uploads, async processing, and GPT action endpoint
"""
import os
import shutil
import traceback
import base64
import tempfile
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException, Request, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from config import settings
from database import get_db, init_db, close_db, Upload, UploadError
from pdf_processor import process_pdf
from embeddings import embedding_service
from qdrant_service import qdrant_service
from reranker import rerank_service
from pdf_annotator import pdf_annotator
from pydantic import BaseModel
from typing import List, Dict, Tuple


# Pydantic models for review endpoints
class ReviewQueryRequest(BaseModel):
    """Request model for /review/query endpoint"""
    paragraphs: List[str]  # Array of paragraph texts from discussion/conclusion
    report_type: str  # Report type to validate and filter


class ParagraphMatch(BaseModel):
    """Individual paragraph match result"""
    text: str
    report_id: str
    section: str
    report_type: str
    page_number: int
    similarity_score: float
    relevance_score: float


class ReviewQueryResponse(BaseModel):
    """Response model for /review/query endpoint"""
    success: bool
    results: List[List[ParagraphMatch]]  # Array of arrays: top 3 matches per input paragraph
    message: str = ""


class AnnotationSpan(BaseModel):
    """Character span for highlighting"""
    start: int
    end: int


class AnnotationRequest(BaseModel):
    """Single annotation with recommendation and spans"""
    paragraph_text: str
    spans: List[List[int]]  # List of [start, end] pairs
    page_hint: int
    recommendation: str


class ReviewAnnotateRequest(BaseModel):
    """Request model for /review/annotate endpoint"""
    pdf_base64: str  # Base64 encoded PDF
    annotations: List[AnnotationRequest]


class ReviewAnnotateByIdRequest(BaseModel):
    """Request model for /review/annotate-by-id endpoint"""
    upload_id: int  # ID of uploaded PDF
    annotations: List[AnnotationRequest]


class ReviewAnnotateResponse(BaseModel):
    """Response model for /review/annotate endpoint"""
    success: bool
    pdf_base64: str = ""  # Annotated PDF in base64
    annotated_count: int = 0
    error_count: int = 0
    errors: List[Dict] = []
    message: str = ""


# Initialize FastAPI app
app = FastAPI(
    title="RAG Backend API",
    description="Custom GPT RAG backend for engineering reports",
    version="1.0.0"
)

# Add CORS middleware for Custom GPT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Custom GPT
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()
    print("✅ Database initialized")
    print(f"✅ Qdrant collection: {settings.qdrant_collection}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    await close_db()
    print("✅ Database connections closed")


# Authentication dependency for GPT action endpoint
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key for GPT action endpoint"""
    if x_api_key != settings.app_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Background processing task
async def process_upload_task(upload_id: int, file_path: str, report_type: str):
    """
    Background task to process uploaded PDF
    Steps: Parse -> Embed -> Index in Qdrant
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    
    # Create new session for background task
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Update status to processing
            result = await db.execute(select(Upload).where(Upload.id == upload_id))
            upload = result.scalar_one_or_none()
            if not upload:
                return
            
            upload.status = "processing"
            await db.commit()
            
            # Step 1: Parse PDF
            try:
                paragraphs = process_pdf(file_path, report_type)
                print(f"✅ Parsed {len(paragraphs)} paragraphs from upload {upload_id}")
            except Exception as e:
                error = UploadError(
                    upload_id=upload_id,
                    stage="parsing",
                    message=str(e),
                    details=traceback.format_exc()
                )
                db.add(error)
                upload.status = "error"
                await db.commit()
                return
            
            # Step 2: Embed paragraphs
            try:
                texts = [p.text for p in paragraphs]
                embeddings = embedding_service.embed_texts(texts)
                print(f"✅ Generated {len(embeddings)} embeddings for upload {upload_id}")
            except Exception as e:
                error = UploadError(
                    upload_id=upload_id,
                    stage="embedding",
                    message=str(e),
                    details=traceback.format_exc()
                )
                db.add(error)
                upload.status = "error"
                await db.commit()
                return
            
            # Step 3: Index in Qdrant
            try:
                # Convert paragraphs to dicts for indexing
                paragraph_dicts = [
                    {
                        "text": p.text,
                        "report_id": p.report_id,
                        "section": p.section,
                        "report_type": p.report_type,
                        "page_number": p.page_number
                    }
                    for p in paragraphs
                ]
                qdrant_service.index_paragraphs(paragraph_dicts, embeddings)
                print(f"✅ Indexed {len(paragraphs)} paragraphs in Qdrant for upload {upload_id}")
            except Exception as e:
                error = UploadError(
                    upload_id=upload_id,
                    stage="qdrant",
                    message=str(e),
                    details=traceback.format_exc()
                )
                db.add(error)
                upload.status = "error"
                await db.commit()
                return
            
            # Success!
            upload.status = "success"
            await db.commit()
            print(f"✅ Upload {upload_id} processed successfully")
            
        except Exception as e:
            print(f"❌ Unexpected error processing upload {upload_id}: {e}")
            upload.status = "error"
            error = UploadError(
                upload_id=upload_id,
                stage="unknown",
                message=str(e),
                details=traceback.format_exc()
            )
            db.add(error)
            await db.commit()
        finally:
            await engine.dispose()


# Web Portal Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    """Home page with upload form and status dashboard"""
    # Get recent uploads
    result = await db.execute(
        select(Upload).order_by(desc(Upload.created_at)).limit(20)
    )
    uploads = result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "uploads": uploads}
    )


@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    report_type: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle PDF upload
    Saves file and queues background processing
    """
    try:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "detail": "Only PDF files are allowed"}
            )
        
        # Create upload record
        upload = Upload(
            file_name=file.filename,
            topic=report_type,
            status="pending"
        )
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        
        # Save uploaded file
        file_path = os.path.join(settings.upload_dir, f"{upload.id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Queue background processing
        background_tasks.add_task(process_upload_task, upload.id, file_path, report_type)
        
        return JSONResponse({
            "success": True,
            "upload_id": upload.id,
            "message": "Upload queued for processing"
        })
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(e)}
        )


@app.get("/uploads/{upload_id}")
async def get_upload_status(upload_id: int, db: AsyncSession = Depends(get_db)):
    """Get status of a specific upload"""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get errors if any
    errors_result = await db.execute(
        select(UploadError).where(UploadError.upload_id == upload_id)
    )
    errors = errors_result.scalars().all()
    
    return {
        "id": upload.id,
        "file_name": upload.file_name,
        "topic": upload.topic,
        "status": upload.status,
        "created_at": upload.created_at.isoformat(),
        "errors": [
            {
                "stage": err.stage,
                "message": err.message,
                "created_at": err.created_at.isoformat()
            }
            for err in errors
        ]
    }


@app.get("/uploads")
async def list_uploads(db: AsyncSession = Depends(get_db)):
    """List all uploads with their status"""
    result = await db.execute(
        select(Upload).order_by(desc(Upload.created_at))
    )
    uploads = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "file_name": u.file_name,
            "topic": u.topic,
            "status": u.status,
            "created_at": u.created_at.isoformat()
        }
        for u in uploads
    ]


# Custom GPT Action Endpoint
@app.post("/api/query")
async def query_reports(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Custom GPT action endpoint
    Accepts query, returns relevant context from reports
    """
    body = await request.json()
    query = body.get("query", "")
    report_type = body.get("report_type")  # Optional filter
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        # Step 1: Embed query
        query_vector = embedding_service.embed_query(query)
        
        # Step 2: Retrieve top 6 similar paragraphs from Qdrant
        initial_results = qdrant_service.search(
            query_vector=query_vector,
            limit=settings.initial_retrieval_count,
            report_type=report_type
        )
        
        if not initial_results:
            return {
                "success": True,
                "results": [],
                "message": "No relevant reports found"
            }
        
        # Step 3: Rerank to get top 3
        reranked_results = rerank_service.rerank(
            query=query,
            documents=initial_results,
            top_k=settings.final_results_count
        )
        
        # Format response for GPT
        formatted_results = []
        for result in reranked_results:
            formatted_results.append({
                "text": result["text"],
                "report_id": result["report_id"],
                "section": result["section"],
                "report_type": result["report_type"],
                "page_number": result["page_number"],
                "similarity_score": result["score"],
                "relevance_score": result["rerank_score"]
            })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }
        
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Review Endpoints for Custom GPT
@app.post("/review/query", response_model=ReviewQueryResponse)
async def review_query(
    request: ReviewQueryRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Custom GPT review endpoint - Query phase
    Accepts paragraphs from discussion/conclusion sections
    Returns top 3 similar paragraphs for each input paragraph
    """
    try:
        # Validate report_type against existing uploads
        result = await db.execute(
            select(Upload).where(Upload.topic == request.report_type).limit(1)
        )
        upload_exists = result.scalar_one_or_none()
        
        if not upload_exists:
            raise HTTPException(
                status_code=400,
                detail=f"Report type '{request.report_type}' not found in database. Please use an existing report type."
            )
        
        all_results = []
        
        # Process each paragraph individually
        for paragraph in request.paragraphs:
            # Step 1: Embed the paragraph
            paragraph_vector = embedding_service.embed_query(paragraph)
            
            # Step 2: Retrieve top 10 similar paragraphs from Qdrant
            initial_results = qdrant_service.search(
                query_vector=paragraph_vector,
                limit=10,  # Search for 10
                report_type=request.report_type
            )
            
            if not initial_results:
                # No matches found, add empty result
                all_results.append([])
                continue
            
            # Step 3: Rerank to get top 3
            reranked_results = rerank_service.rerank(
                query=paragraph,
                documents=initial_results,
                top_k=3  # Rerank to top 3
            )
            
            # Format results for this paragraph
            paragraph_matches = []
            for result in reranked_results:
                paragraph_matches.append(ParagraphMatch(
                    text=result["text"],
                    report_id=result["report_id"],
                    section=result["section"],
                    report_type=result["report_type"],
                    page_number=result["page_number"],
                    similarity_score=result["score"],
                    relevance_score=result["rerank_score"]
                ))
            
            all_results.append(paragraph_matches)
        
        return ReviewQueryResponse(
            success=True,
            results=all_results,
            message=f"Processed {len(request.paragraphs)} paragraphs"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing review query: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review/annotate", response_model=ReviewAnnotateResponse)
async def review_annotate(
    request: ReviewAnnotateRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Custom GPT review endpoint - Annotate phase
    Accepts recommendations with text spans and PDF
    Returns annotated PDF with highlights and sticky notes
    """
    temp_input_path = None
    temp_output_path = None
    
    try:
        # Decode base64 PDF
        try:
            pdf_bytes = base64.b64decode(request.pdf_base64)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 encoding: {str(e)}"
            )
        
        # Validate PDF by attempting to open it
        import fitz
        try:
            # Test if PDF is valid
            test_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            test_doc.close()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupted PDF file: {str(e)}. Please ensure you're uploading a valid, non-scanned PDF exported directly from Word or PDF software."
            )
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as temp_input:
            temp_input.write(pdf_bytes)
            temp_input_path = temp_input.name
        
        temp_output_path = tempfile.mktemp(suffix='.pdf')
        
        # Prepare annotations for pdf_annotator
        annotations = []
        for ann in request.annotations:
            # Convert List[List[int]] to List[Tuple[int, int]]
            spans = [(span[0], span[1]) for span in ann.spans]
            
            annotations.append({
                "paragraph_text": ann.paragraph_text,
                "spans": spans,
                "page_hint": ann.page_hint,
                "recommendation": ann.recommendation
            })
        
        # Annotate PDF
        result = pdf_annotator.annotate_pdf(
            pdf_path=temp_input_path,
            output_path=temp_output_path,
            annotations=annotations
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"PDF annotation failed: {result.get('error', 'Unknown error')}"
            )
        
        # Read annotated PDF and encode to base64
        with open(temp_output_path, 'rb') as f:
            annotated_pdf_bytes = f.read()
            annotated_pdf_base64 = base64.b64encode(annotated_pdf_bytes).decode('utf-8')
        
        return ReviewAnnotateResponse(
            success=True,
            pdf_base64=annotated_pdf_base64,
            annotated_count=result["annotated_count"],
            error_count=result["error_count"],
            errors=result["errors"],
            message=f"Annotated {result['annotated_count']} paragraphs with {result['error_count']} errors"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error processing review annotation: {str(e)}"
        error_trace = traceback.format_exc()
        print(f"❌ {error_msg}")
        print(f"Traceback:\n{error_trace}")
        
        # Return detailed error for debugging
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": type(e).__name__,
                "traceback": error_trace[:500]  # Limit traceback size
            }
        )
    
    finally:
        # Clean up temporary files
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.unlink(temp_input_path)
            except:
                pass
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.unlink(temp_output_path)
            except:
                pass


@app.post("/review/annotate-by-id", response_model=ReviewAnnotateResponse)
async def review_annotate_by_id(
    request: ReviewAnnotateByIdRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Custom GPT review endpoint - Annotate by Upload ID
    References a previously uploaded PDF by its ID
    Returns annotated PDF with highlights and sticky notes
    """
    temp_output_path = None
    
    try:
        # Retrieve upload record
        result = await db.execute(select(Upload).where(Upload.id == request.upload_id))
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail=f"Upload ID {request.upload_id} not found"
            )
        
        # Find the uploaded PDF file
        pdf_path = None
        for file in os.listdir(settings.upload_dir):
            if file.startswith(f"{upload.id}_"):
                pdf_path = os.path.join(settings.upload_dir, file)
                break
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(
                status_code=404,
                detail=f"PDF file for upload ID {request.upload_id} not found on disk"
            )
        
        # Validate PDF can be opened
        import fitz
        try:
            test_doc = fitz.open(pdf_path)
            test_doc.close()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot open PDF file: {str(e)}"
            )
        
        temp_output_path = tempfile.mktemp(suffix='.pdf')
        
        # Prepare annotations for pdf_annotator
        annotations = []
        for ann in request.annotations:
            # Convert List[List[int]] to List[Tuple[int, int]]
            spans = [(span[0], span[1]) for span in ann.spans]
            
            annotations.append({
                "paragraph_text": ann.paragraph_text,
                "spans": spans,
                "page_hint": ann.page_hint,
                "recommendation": ann.recommendation
            })
        
        # Annotate PDF
        result = pdf_annotator.annotate_pdf(
            pdf_path=pdf_path,
            output_path=temp_output_path,
            annotations=annotations
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"PDF annotation failed: {result.get('error', 'Unknown error')}"
            )
        
        # Read annotated PDF and encode to base64
        with open(temp_output_path, 'rb') as f:
            annotated_pdf_bytes = f.read()
            annotated_pdf_base64 = base64.b64encode(annotated_pdf_bytes).decode('utf-8')
        
        return ReviewAnnotateResponse(
            success=True,
            pdf_base64=annotated_pdf_base64,
            annotated_count=result["annotated_count"],
            error_count=result["error_count"],
            errors=result["errors"],
            message=f"Annotated {result['annotated_count']} paragraphs with {result['error_count']} errors"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error processing review annotation by ID: {str(e)}"
        error_trace = traceback.format_exc()
        print(f"❌ {error_msg}")
        print(f"Traceback:\n{error_trace}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": type(e).__name__,
                "traceback": error_trace[:500]
            }
        )
    
    finally:
        # Clean up temporary output file
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.unlink(temp_output_path)
            except:
                pass


@app.get("/review/extract-paragraphs/{upload_id}")
async def extract_paragraphs_from_upload(
    upload_id: int,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract paragraphs from an uploaded PDF for review
    Returns paragraphs from discussion and conclusion sections
    """
    try:
        # Retrieve upload record
        result = await db.execute(select(Upload).where(Upload.id == upload_id))
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail=f"Upload ID {upload_id} not found"
            )
        
        # Find the uploaded PDF file
        pdf_path = None
        for file in os.listdir(settings.upload_dir):
            if file.startswith(f"{upload.id}_"):
                pdf_path = os.path.join(settings.upload_dir, file)
                break
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(
                status_code=404,
                detail=f"PDF file for upload ID {upload_id} not found on disk"
            )
        
        # Extract text from PDF
        import fitz
        doc = fitz.open(pdf_path)
        
        # Extract paragraphs from discussion and conclusion sections
        discussion_paragraphs = []
        conclusion_paragraphs = []
        
        current_section = None
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            # Simple section detection
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line_upper = line.strip().upper()
                
                # Detect section headers
                if 'DISCUSSION' in line_upper and len(line.strip()) < 50:
                    current_section = 'discussion'
                elif 'CONCLUSION' in line_upper and len(line.strip()) < 50:
                    current_section = 'conclusion'
                elif line_upper.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    # New numbered section, reset
                    if 'DISCUSSION' not in line_upper and 'CONCLUSION' not in line_upper:
                        current_section = None
                
                # Collect paragraphs (lines with substantial content)
                if current_section and len(line.strip()) > 50:
                    if current_section == 'discussion':
                        discussion_paragraphs.append({
                            "text": line.strip(),
                            "page": page_num + 1
                        })
                    elif current_section == 'conclusion':
                        conclusion_paragraphs.append({
                            "text": line.strip(),
                            "page": page_num + 1
                        })
        
        doc.close()
        
        return {
            "success": True,
            "upload_id": upload_id,
            "file_name": upload.file_name,
            "report_type": upload.topic,
            "discussion_paragraphs": discussion_paragraphs,
            "conclusion_paragraphs": conclusion_paragraphs,
            "message": f"Extracted {len(discussion_paragraphs)} discussion and {len(conclusion_paragraphs)} conclusion paragraphs"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error extracting paragraphs: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
