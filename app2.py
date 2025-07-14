import os
import uuid
import logging
import uvicorn
import shutil
from dotenv import load_dotenv
from fastapi import (FastAPI, File, UploadFile, 
                     HTTPException, Request, Response)
from pydantic_models_format import (QueryInput, QueryResponse, 
                                    DocumentInfo, DeleteFileRequest)
from langchain_utils import get_rag_chain
from db_utils import  (insert_application_logs, get_chat_history,
                       get_all_documents, insert_document_record, 
                       delete_document_record)
from chroma_utils import index_document_to_chroma, delete_documents_from_chroma

from prometheus_client import (Histogram, Counter, Gauge, 
                               Summary, generate_latest, 
                               CONTENT_TYPE_LATEST)
import psutil
import threading
import time 

logging.basicConfig(filename='application.log', level=logging.INFO)
app = FastAPI()

## ------- Prometheus Metrics --------------
REQUEST_COUNT = Counter("http_requests_total", 
                        "Total HTTP Requests", 
                        ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds",
                             "Request latency in seconds", ["endpoint"])
MODEL_CALLS = Counter("model_calls_total", 
                      "Total model invocations", 
                      ["model"])
UPLOAD_SUCCESS = Counter("upload_success_total", 
                         "Successful document uploads", 
                         ["file_type"])
UPLOAD_FAIL = Counter("upload_fail_total", 
                      "Failed document uploads", 
                      ["file_type"])
NEW_SESSIONS = Counter("new_sessions_total", 
                       "New chat sessions created")

# System monitoring
CPU_USAGE = Gauge("cpu_usage_percent", "CPU usage percentage")
MEMORY_USAGE = Gauge("memory_usage_percent", "Memory usage percentage")
DISK_USAGE = Gauge("disk_usage_percent", "Disk usage percentage")

# Model response tracking
MODEL_ERRORS = Counter("model_errors_total", 
                      "Total model errors", 
                      ["model", "error_type"])

# -------------------------------------
# Middleware for automatic request tracking
# -------------------------------------
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log request count and latency
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)
    
    return response

# ─────────────────────────────
# System Metrics Background Task
# ─────────────────────────────
def track_system_metrics():
    """Background task to continuously monitor system metrics"""
    while True:
        try:
            CPU_USAGE.set(psutil.cpu_percent(interval=None))
            MEMORY_USAGE.set(psutil.virtual_memory().percent)
            DISK_USAGE.set(psutil.disk_usage("/").percent)
        except Exception as e:
            logging.error(f"Error tracking system metrics: {e}")
        time.sleep(5)

@app.on_event("startup")
def start_system_monitoring():
    """Start background system monitoring thread"""
    threading.Thread(target=track_system_metrics, daemon=True).start()
    logging.info("System monitoring started")

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/chat", response_model=QueryResponse)
def chat(query_input: QueryInput):
    """Handle chat queries with RAG chain"""
    session_id = query_input.session_id
    logging.info(f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}")
    
    # Generate new session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        NEW_SESSIONS.inc()
    
    try:
        # Get chat history
        chat_history = get_chat_history(session_id)
        
        # Get RAG chain
        rag_chain = get_rag_chain(query_input.model.value)
        
        # Track model call
        MODEL_CALLS.labels(model=query_input.model.value).inc()
        
        # Invoke RAG chain
        result = rag_chain.invoke({
            "input": query_input.question,
            "chat_history": chat_history
        })
        
        answer = result['answer']
        print("Answer:", answer)
        
        # Log to database
        insert_application_logs(session_id, query_input.question, answer, query_input.model.value)
        logging.info(f"Session ID: {session_id}, AI Response: {answer}")
        
        return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)
        
    except Exception as e:
        # Track model errors
        MODEL_ERRORS.labels(model=query_input.model.value, error_type=type(e).__name__).inc()
        logging.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/upload-document")
def upload_document(file: UploadFile = File(...)):
    """Upload and index document"""
    allowed_extensions = ['.pdf', '.docx', '.html']
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        UPLOAD_FAIL.labels(file_type=file_extension).inc()
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
    
    temp_file_path = f"temp_{file.filename}"
    file_id = None
    
    try:
        # Save the uploaded file to temp files
        with open(temp_file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Insert document record
        file_id = insert_document_record(file.filename)
        
        # Index document to Chroma
        success = index_document_to_chroma(temp_file_path, file_id)
        
        if success:
            UPLOAD_SUCCESS.labels(file_type=file_extension).inc()
            logging.info(f"Successfully uploaded and indexed: {file.filename}")
            return {"message": f"File {file.filename} has been added successfully"}
        else:
            UPLOAD_FAIL.labels(file_type=file_extension).inc()
            if file_id:
                delete_document_record(file_id)
            raise HTTPException(status_code=500, detail=f"Failed to index {file.filename}")
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        UPLOAD_FAIL.labels(file_type=file_extension).inc()
        logging.error(f"Error uploading document {file.filename}: {e}")
        if file_id:
            delete_document_record(file_id)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    """Get list of all documents"""
    try:
        return get_all_documents()
    except Exception as e:
        logging.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving documents")

@app.post("/delete-doc")
def delete_document(request: DeleteFileRequest):
    """Delete document from both Chroma and database"""
    try:
        # Delete from Chroma
        chroma_delete_success = delete_documents_from_chroma(request.file_id)
        
        if chroma_delete_success:
            # Delete from database
            db_delete_success = delete_document_record(request.file_id)
            
            if db_delete_success:
                logging.info(f"Successfully deleted document with file ID: {request.file_id}")
                return {"message": f"Successfully deleted document with file ID {request.file_id}"}
            else:
                logging.error(f"Deleted from Chroma but failed to delete document {request.file_id} from database")
                return {"error": f"Deleted from Chroma but failed to delete document {request.file_id} from database"}
        else:
            logging.error(f"Failed to delete document with file ID {request.file_id} from Chroma")
            return {"error": f"Failed to delete document with file ID {request.file_id} from Chroma"}
            
    except Exception as e:
        logging.error(f"Error deleting document {request.file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)