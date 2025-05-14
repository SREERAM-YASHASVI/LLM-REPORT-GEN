import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import Visualization from './Visualization';

interface ThinkingStep {
  type: 'thinking' | 'conclusion';
  content: string;
}

interface Task {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  result?: string;
  error?: string;
  thinking_steps?: ThinkingStep[];
  visualizations?: {
    chart_type: string;
    title: string;
    x_axis: string;
    y_axis: string;
    data: any[];
    options?: any;
  }[];
}

// Add new state for search mode
type SearchMode = 'keyword' | 'semantic';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [uploading, setUploading] = useState(false);
  const [querying, setQuerying] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [allTags, setAllTags] = useState<any[]>([]);
  const [tagManagerDocId, setTagManagerDocId] = useState<number | null>(null);
  const [docTags, setDocTags] = useState<{ [docId: number]: any[] }>({});
  const [tagLoading, setTagLoading] = useState(false);
  const [tagError, setTagError] = useState<string | null>(null);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState('');

  // UI toggles
  const [showDocs, setShowDocs] = useState(true);

  useEffect(() => {
    // Fetch document list from backend
    const fetchDocuments = async () => {
      setDocumentsLoading(true);
      setDocumentsError(null);
      try {
        const response = await fetch('/documents');
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch documents');
        }
        setDocuments(data.documents || []);
      } catch (error) {
        setDocumentsError(error instanceof Error ? error.message : 'Failed to fetch documents');
      } finally {
        setDocumentsLoading(false);
      }
    };
    fetchDocuments();
  }, []);

  // Fetch all tags on mount
  useEffect(() => {
    const fetchTags = async () => {
      try {
        const response = await fetch('/tags');
        const data = await response.json();
        if (response.ok) setAllTags(data.tags || []);
      } catch {}
    };
    fetchTags();
  }, []);

  // Fetch tags for a document
  const fetchDocTags = async (docId: number) => {
    setTagLoading(true);
    setTagError(null);
    try {
      const response = await fetch(`/documents/${docId}/tags`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to fetch tags');
      setDocTags(prev => ({ ...prev, [docId]: data.tags.map((t: any) => ({ id: t.tag_id, name: t.tags.name, color: t.tags.color })) }));
    } catch (e: any) {
      setTagError(e.message || 'Failed to fetch tags');
    } finally {
      setTagLoading(false);
    }
  };

  // Open tag manager for a document
  const openTagManager = (docId: number) => {
    setTagManagerDocId(docId);
    fetchDocTags(docId);
  };
  const closeTagManager = () => setTagManagerDocId(null);

  // Add tag to document
  const addTagToDoc = async (docId: number, tagId: number) => {
    setTagLoading(true);
    setTagError(null);
    // Optimistically update UI
    setDocTags(prev => {
      const prevTags = prev[docId] || [];
      if (prevTags.some(t => t.id === tagId)) return prev; // already present
      const tagObj = allTags.find(t => t.id === tagId);
      return { ...prev, [docId]: [...prevTags, tagObj] };
    });
    try {
      const response = await fetch(`/documents/${docId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_id: tagId })
      });
      if (!response.ok) throw new Error('Failed to add tag');
      await fetchDocTags(docId); // sync with backend
    } catch (e: any) {
      setTagError(e.message || 'Failed to add tag');
      // Revert optimistic update
      setDocTags(prev => {
        const prevTags = prev[docId] || [];
        return { ...prev, [docId]: prevTags.filter(t => t.id !== tagId) };
      });
    } finally {
      setTagLoading(false);
    }
  };

  // Remove tag from document
  const removeTagFromDoc = async (docId: number, tagId: number) => {
    setTagLoading(true);
    setTagError(null);
    // Optimistically update UI
    setDocTags(prev => {
      const prevTags = prev[docId] || [];
      return { ...prev, [docId]: prevTags.filter(t => t.id !== tagId) };
    });
    try {
      const response = await fetch(`/documents/${docId}/tags/${tagId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to remove tag');
      await fetchDocTags(docId); // sync with backend
    } catch (e: any) {
      setTagError(e.message || 'Failed to remove tag');
      // Revert optimistic update
      setDocTags(prev => {
        const prevTags = prev[docId] || [];
        const tagObj = allTags.find(t => t.id === tagId);
        return { ...prev, [docId]: [...prevTags, tagObj] };
      });
    } finally {
      setTagLoading(false);
    }
  };

  // Create a new tag
  const createTag = async () => {
    if (!newTagName.trim()) return;
    setTagLoading(true);
    setTagError(null);
    try {
      const response = await fetch('/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTagName.trim(), color: newTagColor.trim() })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to create tag');
      setNewTagName('');
      setNewTagColor('');
      // Refresh all tags
      const tagsResp = await fetch('/tags');
      const tagsData = await tagsResp.json();
      if (tagsResp.ok) setAllTags(tagsData.tags || []);
    } catch (e: any) {
      setTagError(e.message || 'Failed to create tag');
    } finally {
      setTagLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files[0]) {
      const selectedFile = files[0];
      // CSV file type validation
      if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
        setUploadError('Only CSV files are supported.');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setUploadError(null);
      const formData = new FormData();
      formData.append('file', selectedFile);
      try {
        setUploading(true);
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData,
        });
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
          }
          setUploadedFiles((prev) => [...prev, selectedFile.name]);
          console.log('Upload successful:', data);
        } else {
          const text = await response.text();
          throw new Error('Non-JSON response: ' + text);
        }
      } catch (error) {
        console.error('Upload error:', error);
        setUploadError(error instanceof Error ? error.message : 'Failed to upload file');
        setFile(null);
      } finally {
        setUploading(false);
      }
    }
  };

  const handleQuerySubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;

    const newTask: Task = {
      id: Date.now().toString(),
      status: 'pending',
    };
    setTasks([...tasks, newTask]);

    try {
      setQuerying(true);
      const response = await fetch('/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Query failed');
      }

      setTasks(tasks => tasks.map(task => 
        task.id === newTask.id 
          ? { 
              ...task, 
              status: 'completed', 
              result: data.response.response,
              visualizations: data.response.visualizations,
              thinking_steps: data.response.insights
            }
          : task
      ));
      setQuery('');
    } catch (error) {
      console.error('Query error:', error);
      setTasks(tasks => tasks.map(task => 
        task.id === newTask.id 
          ? { 
              ...task, 
              status: 'error', 
              error: error instanceof Error ? error.message : 'Failed to process query'
            }
          : task
      ));
    } finally {
      setQuerying(false);
    }
  };

  // Helper: get tags for a document
  const getTagsForDoc = (docId: number) => docTags[docId] || [];

  // Helper: get document metadata by id
  const getDocMeta = (docId: number) => documents.find((d: any) => d.id === docId);

  return (
    <div className="App" style={{ fontFamily: 'Inter, Segoe UI, Arial, sans-serif' }}>
      <header className="App-header">
        <h1 style={{ textAlign: 'center', width: '100%' }}>LLM Report Gen</h1>
      </header>
      <main className="App-main" style={{ maxWidth: 700, margin: '0 auto', padding: '32px 12px 40px 12px', display: 'flex', flexDirection: 'column', gap: 32 }}>
        {/* Toggle for Upload/All Documents */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
          <button
            onClick={() => setShowDocs((v) => !v)}
            aria-pressed={showDocs}
            aria-label={showDocs ? 'Hide document sections' : 'Show document sections'}
            style={{
              marginRight: 16,
              padding: '8px 18px',
              borderRadius: 8,
              border: 'none',
              background: showDocs ? '#6c63ff' : '#e0e7ff',
              color: showDocs ? '#fff' : '#222',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: 16,
              boxShadow: showDocs ? '0 2px 8px rgba(76,99,255,0.08)' : 'none',
              transition: 'background 0.2s, color 0.2s',
            }}
          >
            {showDocs ? 'Hide' : 'Show'} Upload & Documents
          </button>
          <span style={{ color: '#888', fontSize: 15 }}>
            {showDocs ? 'Document upload and list are visible.' : 'Document upload and list are hidden.'}
          </span>
        </div>

        {/* Upload and All Documents sections, toggled */}
        {showDocs && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
            <section className="upload-section" aria-label="Upload Document" style={{ marginBottom: 0 }}>
              <h2>Upload Document</h2>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                disabled={uploading || querying}
                aria-label="Upload CSV file"
              />
              <p>Only CSV files are supported.</p>
              {file && <p className="success">Selected file: {file.name}</p>}
              {uploadError && <p className="error">{uploadError}</p>}
              {uploadedFiles.length > 0 && (
                <div className="uploaded-list">
                  <h4>Uploaded CSVs:</h4>
                  <ul>
                    {uploadedFiles.map((fname, idx) => (
                      <li key={idx}>{fname}</li>
                    ))}
                  </ul>
                </div>
              )}
            </section>

          </div>
        )}
        {/* Move All Documents section outside the upload section, but still within the toggled area */}
        {showDocs && (
          <section className="document-list-section" aria-label="All Documents" style={{ marginBottom: 0 }}>
            <h2>All Documents</h2>
            {documentsLoading ? (
              <div style={{ color: '#888' }}>Loading documents...</div>
            ) : documentsError ? (
              <div className="error-message">{documentsError}</div>
            ) : documents.length === 0 ? (
              <div style={{ color: '#888' }}>No documents found.</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
                <thead>
                  <tr style={{ background: '#f0f1f6' }}>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Filename</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Upload Date</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>File Size</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px' }}>Tags</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '6px 8px' }}>{doc.filename}</td>
                      <td style={{ padding: '6px 8px' }}>{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : '-'}</td>
                      <td style={{ padding: '6px 8px' }}>{doc.file_size ? `${doc.file_size} bytes` : '-'}</td>
                      <td style={{ padding: '6px 8px' }}>
                        {(docTags[doc.id] || []).length === 0 ? (
                          <span style={{ color: '#aaa' }}>No tags</span>
                        ) : (
                          docTags[doc.id].map((tag: any) => (
                            <span key={tag.id} style={{
                              display: 'inline-block',
                              background: tag.color || '#e0e7ff',
                              color: '#222',
                              borderRadius: 8,
                              padding: '2px 8px',
                              marginRight: 4,
                              fontSize: 13,
                              marginBottom: 2
                            }}>{tag.name}
                              <button onClick={() => removeTagFromDoc(doc.id, tag.id)} style={{ marginLeft: 4, border: 'none', background: 'none', color: '#e63946', cursor: 'pointer', fontWeight: 'bold' }} title="Remove tag">×</button>
                            </span>
                          ))
                        )}
                      </td>
                      <td style={{ padding: '6px 8px' }}>
                        <button onClick={() => openTagManager(doc.id)} style={{ fontSize: 13 }}>Manage Tags</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {/* Tag Manager Modal/Popup */}
            {tagManagerDocId && (
              <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.18)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ background: '#fff', borderRadius: 12, padding: 24, minWidth: 320, boxShadow: '0 2px 16px rgba(0,0,0,0.13)' }}>
                  <h3>Manage Tags</h3>
                  {tagLoading ? <div>Loading...</div> : tagError ? <div className="error-message">{tagError}</div> : (
                    <>
                      <div style={{ marginBottom: 10 }}>
                        <strong>Current Tags:</strong>
                        <div style={{ marginTop: 6 }}>
                          {(docTags[tagManagerDocId] || []).length === 0 ? <span style={{ color: '#aaa' }}>No tags</span> : docTags[tagManagerDocId].map((tag: any) => (
                            <span key={tag.id} style={{
                              display: 'inline-block',
                              background: tag.color || '#e0e7ff',
                              color: '#222',
                              borderRadius: 8,
                              padding: '2px 8px',
                              marginRight: 4,
                              fontSize: 13,
                              marginBottom: 2
                            }}>{tag.name}
                              <button onClick={() => removeTagFromDoc(tagManagerDocId, tag.id)} style={{ marginLeft: 4, border: 'none', background: 'none', color: '#e63946', cursor: 'pointer', fontWeight: 'bold' }} title="Remove tag">×</button>
                            </span>
                          ))}
                        </div>
                      </div>
                      <div style={{ marginBottom: 10 }}>
                        <strong>Add Tag:</strong>
                        <div style={{ marginTop: 6 }}>
                          <select onChange={e => addTagToDoc(tagManagerDocId, Number(e.target.value))} value="">
                            <option value="">Select tag...</option>
                            {allTags.filter(t => !(docTags[tagManagerDocId] || []).some((dt: any) => dt.id === t.id)).map((tag: any) => (
                              <option key={tag.id} value={tag.id}>{tag.name}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div style={{ marginBottom: 10 }}>
                        <strong>Create New Tag:</strong>
                        <div style={{ marginTop: 6 }}>
                          <input type="text" placeholder="Tag name" value={newTagName} onChange={e => setNewTagName(e.target.value)} style={{ marginRight: 6 }} />
                          <input type="color" value={newTagColor} onChange={e => setNewTagColor(e.target.value)} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                          <button onClick={createTag} disabled={tagLoading || !newTagName.trim()}>Create</button>
                        </div>
                      </div>
                    </>
                  )}
                  <div style={{ marginTop: 18, textAlign: 'right' }}>
                    <button onClick={closeTagManager}>Close</button>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Centered Query Section */}
        <section className="query-section" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', margin: '0 auto', maxWidth: 480, width: '100%' }}>
          <h2 style={{ textAlign: 'center' }}>Ask a Question</h2>
          <form onSubmit={handleQuerySubmit} style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your question..."
              disabled={querying || !file}
              style={{ width: '100%', maxWidth: 340, marginBottom: 12, fontSize: 16, padding: 10, borderRadius: 8, border: '1px solid #e0e0e0' }}
              aria-label="Enter your question"
            />
            <button
              type="submit"
              disabled={querying || !file || !query.trim()}
              style={{ width: 180, fontSize: 16, padding: '10px 0', borderRadius: 8 }}
            >
              {querying ? 'Processing...' : 'Submit Query'}
            </button>
          </form>
        </section>

        <section className="results-section" style={{ marginTop: 24 }}>
          <h2>Results</h2>
          {querying && (
            <div style={{ textAlign: 'center', margin: '20px 0' }}>
              <span className="spinner" style={{ display: 'inline-block', width: 32, height: 32, border: '4px solid #ccc', borderTop: '4px solid #8884d8', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></span>
              <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
              <div style={{ marginTop: 8, color: '#888' }}>Loading analysis...</div>
            </div>
          )}
          {tasks.length === 0 ? (
            <p>No queries yet</p>
          ) : (
            <ul className="tasks-list">
              {tasks.map((task) => (
                <li key={task.id} className={`task-item ${task.status}`}>
                  <div className="task-status">
                    {task.result}
                  </div>
                  
                  {task.thinking_steps && task.thinking_steps.length > 0 && (
                    <div className="thinking-steps">
                      <h3>Thinking Process:</h3>
                      {task.thinking_steps.map((step, index) => (
                        <div key={index} className={`thinking-step ${step.type}`}>
                          <div className="step-type">
                            {step.type === 'thinking' ? '🤔 Thinking:' : '💡 Conclusion:'}
                          </div>
                          <div className="step-content">{step.content}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {task.result && (
                    <div className="task-result">
                      <h3>Final Answer:</h3>
                      <div>{task.result}</div>
                      {task.visualizations && task.visualizations.length > 0 ? (
                        <div className="visualizations">
                          {task.visualizations.map((chart, idx) => {
                            const normalized = chart.data.map(d => ({ name: d[chart.x_axis], value: d[chart.y_axis] }));
                            return (
                              <div key={idx} className="chart-container">
                                <h4>{chart.title}</h4>
                                <Visualization chartData={normalized} />
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div style={{ color: '#888', marginTop: '10px' }}>No visualizations available for this result.</div>
                      )}
                    </div>
                  )}
                  
                  {task.error && (
                    <div className="task-error">{task.error}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;

