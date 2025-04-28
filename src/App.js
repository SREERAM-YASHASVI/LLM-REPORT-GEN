import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Box, 
  Container, 
  Typography, 
  Button, 
  TextField,
  Paper,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Collapse
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import UploadFileIcon from '@mui/icons-material/UploadFile';

function App() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [showThinking, setShowThinking] = useState(false);
  const [thinkingProcess, setThinkingProcess] = useState('');

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          setDocuments(prevDocs => [...prevDocs, { ...file, id: result.doc_id }]);
        } else {
          console.error('Upload failed');
        }
      } catch (error) {
        console.error('Error uploading file:', error);
      }
    }
  };

  const removeDocument = (index) => {
    setDocuments(prevDocs => prevDocs.filter((_, i) => i !== index));
  };

  const handleQuery = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: query,
          doc_ids: documents.map(doc => doc.id)
        }),
      });

      const result = await response.json();
      if (response.ok) {
        // Check if response contains thinking process
        if (result.response.includes('<think>')) {
          const thinkMatch = result.response.match(/<think>(.*?)<\/think>/s);
          if (thinkMatch) {
            setThinkingProcess(thinkMatch[1].trim());
            setResponse(result.response.split('</think>')[1].trim());
          } else {
            setResponse(result.response);
          }
        } else {
          setResponse(result.response);
        }
      } else {
        console.error('Server error:', result);
        setResponse(`Error: ${result.detail || 'Failed to get response from server'}`);
      }
    } catch (error) {
      console.error('Error querying documents:', error);
      setResponse('Error: Failed to connect to server');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Document Query System
        </Typography>

        {/* Document Upload Section */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Upload Documents
          </Typography>
          <Button
            variant="contained"
            component="label"
            startIcon={<UploadFileIcon />}
            sx={{ mb: 2 }}
          >
            Upload Files
            <input
              type="file"
              hidden
              multiple
              onChange={handleFileUpload}
            />
          </Button>

          <List>
            {documents.map((file, index) => (
              <ListItem
                key={index}
                secondaryAction={
                  <IconButton edge="end" onClick={() => removeDocument(index)}>
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemText 
                  primary={file.name}
                  secondary={
                    <Typography variant="caption" color="success.main">
                      ✓ Uploaded successfully
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Paper>

        {/* Query Section */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Ask Questions
          </Typography>
          <TextField
            fullWidth
            label="Enter your query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            margin="normal"
          />
          <Button 
            variant="contained" 
            onClick={handleQuery}
            disabled={documents.length === 0 || !query.trim()}
            sx={{ mt: 2 }}
          >
            {isLoading ? 'Processing...' : 'Submit Query'}
          </Button>

          {response && (
            <Paper sx={{ p: 2, mt: 2, bgcolor: 'grey.50' }}>
              {thinkingProcess && (
                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setShowThinking(!showThinking)}
                    sx={{ mb: 1 }}
                  >
                    {showThinking ? 'Hide Thinking Process' : 'Show Thinking Process'}
                  </Button>
                  <Collapse in={showThinking}>
                    <Paper sx={{ p: 2, bgcolor: 'grey.100', mb: 2 }}>
                      <Box sx={{ 
                        '& p': { mt: 1, mb: 1 },
                        '& ul': { mt: 1, mb: 1 },
                        '& li': { mt: 0.5 },
                        '& strong': { fontWeight: 'bold' },
                        color: 'text.secondary'
                      }}>
                        <ReactMarkdown>
                          {thinkingProcess}
                        </ReactMarkdown>
                      </Box>
                    </Paper>
                  </Collapse>
                </Box>
              )}
              <Box sx={{ 
                '& p': { mt: 1, mb: 1 },
                '& ul': { mt: 1, mb: 1, pl: 2 },
                '& li': { mt: 0.5, listStyleType: 'disc' },
                '& strong': { 
                  fontWeight: 700,
                  color: 'primary.main'
                },
                '& p strong': {
                  display: 'inline-block',
                  position: 'relative',
                  '&::before, &::after': {
                    content: '"**"',
                    color: 'text.secondary',
                    opacity: 0.5,
                    fontWeight: 400
                  }
                }
              }}>
                <ReactMarkdown>
                  {response}
                </ReactMarkdown>
              </Box>
            </Paper>
          )}
        </Paper>
      </Box>
    </Container>
  );
}

export default App;
