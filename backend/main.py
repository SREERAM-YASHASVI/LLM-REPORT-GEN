from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crew_agents import DocumentAnalysisCrew
import os
import logging
import httpx
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DocumentAnalysisCrew
crew = DocumentAnalysisCrew()

# Store uploaded documents
uploaded_documents = []

class Query(BaseModel):
    text: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)
        
        # Save file to uploads directory
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # Add file to uploaded documents list
        uploaded_documents.append({
            "name": file.filename,
            "path": file_path
        })
        
        logger.info(f"Successfully uploaded file: {file.filename}")
        return {"filename": file.filename, "status": "success"}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return {"error": str(e)}

@app.post("/query")
async def query_documents(query: Query):
    try:
        if not uploaded_documents:
            logger.warning("Query attempted with no documents uploaded")
            return {"error": "No documents uploaded yet"}

        logger.info(f"Processing query: {query.text}")
        # Process query using Crew AI
        try:
            result = await crew.process_query(
                query.text,
                [doc["path"] for doc in uploaded_documents]
            )
            return {"response": result}
        except Exception as e:
            if "Ollama server is not available" in str(e):
                raise HTTPException(status_code=503, detail="Ollama server is not available")
            raise

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {"error": str(e)}

@app.get("/documents")
async def get_documents():
    return {"documents": [doc["name"] for doc in uploaded_documents]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
