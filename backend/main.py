from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
from typing import List
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store uploaded documents in memory (for demo purposes)
documents = {}

class Query(BaseModel):
    text: str
    doc_ids: List[str]

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    doc_id = file.filename
    documents[doc_id] = content.decode('utf-8')
    return {"doc_id": doc_id}

@app.post("/query")
async def query_documents(query: Query):
    if not query.doc_ids:
        raise HTTPException(status_code=400, detail="No documents selected")

    # Prepare context from selected documents
    context = ""
    for doc_id in query.doc_ids:
        if doc_id in documents:
            context += f"\nDocument: {doc_id}\n{documents[doc_id]}\n"

    # Prepare prompt for Ollama
    prompt = f"""Context: {context}

Question: {query.text}

Please provide a concise answer based on the context provided above."""

    try:
        logger.info(f"Processing query for documents: {query.doc_ids}")
        logger.info(f"Constructed prompt: {prompt}")

        # Check if Ollama is running
        async with httpx.AsyncClient() as client:
            try:
                health_check = await client.get("http://localhost:11434/api/tags")
                if health_check.status_code != 200:
                    logger.error("Ollama server is not responding properly")
                    raise HTTPException(status_code=503, detail="Ollama server is not available")
            except httpx.ConnectError:
                logger.error("Could not connect to Ollama server")
                raise HTTPException(status_code=503, detail="Could not connect to Ollama server")

            # Call Ollama API
            try:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "deepseek-r1:1.5b",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Ollama API error: {error_detail}")
                    raise HTTPException(status_code=500, detail=f"Error from Ollama API: {error_detail}")
                
                result = response.json()
                if "response" not in result:
                    logger.error(f"Unexpected response format: {result}")
                    raise HTTPException(status_code=500, detail="Unexpected response format from Ollama")
                
                return {"response": result["response"]}
                
            except httpx.TimeoutError:
                logger.error("Ollama API request timed out")
                raise HTTPException(status_code=504, detail="Request to Ollama timed out")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
