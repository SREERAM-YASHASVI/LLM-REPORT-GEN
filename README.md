# Document Query App

A web application that allows users to upload documents and query their contents using the Ollama AI model.

## Features

- Document upload functionality
- AI-powered document querying using Ollama
- Interactive UI with collapsible thinking process
- Markdown support for formatted responses
- Real-time status updates

## Setup

### Backend

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Start the backend server:
```bash
python main.py
```

### Frontend

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the frontend development server:
```bash
npm start
```

## Usage

1. Access the application at http://localhost:3000
2. Upload documents using the "Upload Files" button
3. Enter your query in the text field
4. Click "Submit Query" to get AI-powered responses
5. Use the "Show/Hide Thinking Process" button to view the AI's reasoning

## Technologies Used

- Frontend: React, Material-UI, React-Markdown
- Backend: FastAPI, Python
- AI: Ollama (deepseek-r1:1.5b model)
