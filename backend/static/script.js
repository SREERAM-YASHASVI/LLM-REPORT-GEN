
    async function submitQuery() {
        const question = document.getElementById('question').value;
        const docPath = document.getElementById('doc-path').value;
        
        if (!question) {
            alert('Please enter a question');
            return;
        }
        
        const documents = docPath ? [docPath] : [];
        
        document.getElementById('response').textContent = 'Processing...';
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question, documents })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('response').textContent = data.response;
            } else {
                document.getElementById('response').textContent = `Error: ${data.error}`;
            }
        } catch (error) {
            document.getElementById('response').textContent = `Error: ${error.message}`;
        }
    }
    