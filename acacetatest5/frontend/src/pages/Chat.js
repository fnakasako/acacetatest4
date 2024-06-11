import React, { useState } from 'react';
import axios from 'axios';

function Chat() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  const submitQuery = async () => {
    const response = await axios.post('http://localhost:5000/api/search', { query });
    setResults(response.data);
  };

  return (
    <div>
      <h1>Chat with our Document Retrieval System</h1>
      <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Enter your query" />
      <button onClick={submitQuery}>Search</button>
      <div>
        {results.map((result, index) => (
          <div key={index}>
            <h2>{result.filename}</h2>
            <p>{result.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Chat;
