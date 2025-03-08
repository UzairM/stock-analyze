import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';

const Upload = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
    setSuccess(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    
    if (file.type !== 'text/csv') {
      setError('Please upload a CSV file');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      setUploading(true);
      await axios.post(`${API_URL}/companies/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setSuccess(true);
      setUploading(false);
      setFile(null);
    } catch (err) {
      setError('Error uploading file: ' + err.message);
      setUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <Link to="/" className="back-link">← Back to Companies</Link>
      
      <h1>Upload Companies CSV</h1>
      
      <div className="upload-instructions">
        <h2>Instructions</h2>
        <p>Upload a CSV file with the following headers:</p>
        <code>
          ticker, name, sector, industry, country, exchange, market_cap, employees, incorporation_date, website, 
          totalRevenue, grossProfits, ebitda, operatingMargins, returnOnAssets, returnOnEquity, 
          currentPrice, targetHighPrice, targetLowPrice, targetMeanPrice, recommendationMean
        </code>
      </div>
      
      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-group">
          <label htmlFor="file-upload">Select CSV File:</label>
          <input
            type="file"
            id="file-upload"
            accept=".csv"
            onChange={handleFileChange}
            disabled={uploading}
          />
        </div>
        
        {error && <div className="error">{error}</div>}
        {success && <div className="success">File uploaded successfully!</div>}
        
        <button 
          type="submit" 
          className="upload-button" 
          disabled={!file || uploading}
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
    </div>
  );
};

export default Upload; 