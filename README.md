# LLM Report Gen

A web application for uploading CSV documents, querying their contents using LLMs (Ollama, CrewAI), tagging, and visualizing results interactively. The app uses Supabase for storage, chunking, and metadata management.

## Features

- Upload and manage CSV documents
- Tag documents and filter by tags
- AI-powered document querying using CrewAI and Ollama
- Interactive UI with separate Upload and All Documents sections
- Real-time status and thinking process visualization
- Data visualization using Recharts (frontend-generated charts)
- Supabase integration for document storage, chunking, and metadata
- Rate limiting to prevent abuse (leaky bucket algorithm)

## Project Structure

```
document-query-app/
├── backend/      # FastAPI backend, CrewAI, Ollama, Supabase
├── frontend/     # React frontend, Recharts, document/tag UI
└── README.md     # (this file)
```

## Setup

### Backend

1. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend

1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start the frontend development server:
   ```bash
   npm start
   ```

## Usage

1. Access the app at [http://localhost:3000](http://localhost:3000)
2. Upload CSV documents using the Upload section
3. View all uploaded documents in the All Documents section
4. Tag documents and manage tags
5. Enter your query and submit
6. View AI-powered responses, thinking process, and (if applicable) data visualizations

## API Endpoints

- `POST /upload` — Upload a document (multipart/form-data)
- `POST /query` — Query uploaded documents (JSON: `{ "query": "..." }`)
- `GET /documents` — List uploaded documents
- `GET /tags` — List all tags
- `POST /tags` — Create a new tag
- `POST /documents/{id}/tags` — Add a tag to a document
- `DELETE /documents/{id}/tags/{tag_id}` — Remove a tag from a document

**Rate Limiting:**
- Each endpoint is protected by a leaky bucket rate limiter (default: 10 requests, leaks 2/sec). Exceeding the limit returns HTTP 429.

## Visualization

- The frontend uses [Recharts](https://recharts.org/) to display charts based on query results.
- If the backend returns structured data (e.g., `{ chartData: [...] }`), it is visualized automatically.
- The frontend normalizes arrays and can display mock data for demonstration if keywords like "data" or "trend" are detected in the response.
- To extend: Update the backend to return a `chartData` field for queries that should be visualized.

## Technologies Used

- **Frontend**: React, Recharts, CSS
- **Backend**: FastAPI, Python, CrewAI, Ollama, Supabase
- **AI**: Ollama (deepseek-r1:1.5b model)
- **Rate Limiting**: Custom leaky bucket implementation

---
For more details, see the code in the `backend/` and `frontend/` directories.
