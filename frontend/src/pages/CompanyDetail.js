import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';

const CompanyDetail = () => {
  const { id } = useParams();
  const [company, setCompany] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    const fetchCompanyData = async () => {
      try {
        setLoading(true);
        // Fetch company details
        const companyResponse = await axios.get(`${API_URL}/companies/${id}`);
        setCompany(companyResponse.data);
        
        // Fetch analyses for this company
        const analysesResponse = await axios.get(`${API_URL}/analyses/company/${id}`);
        setAnalyses(analysesResponse.data);
        
        setLoading(false);
      } catch (err) {
        setError('Error fetching company data: ' + err.message);
        setLoading(false);
      }
    };

    fetchCompanyData();
  }, [id]);

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      setError(null);
      
      // Show a message to the user
      console.log('Starting analysis...');
      
      // Use the direct analysis endpoint 
      const response = await axios.post(`${API_URL}/analyses/ticker/${id}`);
      console.log('Analysis started:', response.data);
      
      // Add the new analysis to the analyses array
      if (response.data) {
        setAnalyses(prevAnalyses => [response.data, ...prevAnalyses]);
        
        // Poll for status updates every 5 seconds
        const checkStatus = async () => {
          try {
            // Get the analysis ID from the response
            const analysisId = response.data._id;
            
            // Get the latest status
            const statusResponse = await axios.get(`${API_URL}/analyses/${analysisId}`);
            console.log('Analysis status:', statusResponse.data);
            
            // Update the analysis in the list
            const updatedAnalysis = statusResponse.data;
            setAnalyses(prevAnalyses => 
              prevAnalyses.map(analysis => 
                analysis._id === analysisId ? updatedAnalysis : analysis
              )
            );
            
            // Check if the analysis is complete
            const status = updatedAnalysis.status || '';
            if (status === 'completed' || status === 'failed') {
              setAnalyzing(false);
              console.log('Analysis complete:', status);
            } else {
              // Check again in 5 seconds
              setTimeout(checkStatus, 5000);
            }
          } catch (err) {
            console.error('Error checking status:', err);
            setAnalyzing(false);
          }
        };
        
        // Start checking status
        checkStatus();
      } else {
        setAnalyzing(false);
      }
    } catch (err) {
      console.error('Analysis error:', err);
      setError('Error performing analysis: ' + (err.response?.data?.detail || err.message));
      setAnalyzing(false);
    }
  };

  if (loading) {
    return <div>Loading company data...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!company) {
    return <div>Company not found</div>;
  }

  // Get the most recent analysis
  const latestAnalysis = analyses.length > 0 ? analyses[0] : null;

  return (
    <div className="company-detail">
      <Link to="/" className="back-link">← Back to Companies</Link>
      
      <h1>{company.name} ({company.ticker})</h1>
      
      <div className="company-info">
        <h2>Company Information</h2>
        <div className="info-grid">
          <div className="info-item">
            <strong>Sector:</strong> {company.sector || 'N/A'}
          </div>
          <div className="info-item">
            <strong>Industry:</strong> {company.industry || 'N/A'}
          </div>
          <div className="info-item">
            <strong>Country:</strong> {company.country || 'N/A'}
          </div>
          <div className="info-item">
            <strong>Exchange:</strong> {company.exchange || 'N/A'}
          </div>
          <div className="info-item">
            <strong>Market Cap:</strong> {company.market_cap ? `$${company.market_cap.toLocaleString()}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Employees:</strong> {company.employees ? company.employees.toLocaleString() : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Website:</strong> {company.website ? <a href={company.website} target="_blank" rel="noopener noreferrer">{company.website}</a> : 'N/A'}
          </div>
        </div>
        
        <h2>Financial Metrics</h2>
        <div className="info-grid">
          <div className="info-item">
            <strong>Total Revenue:</strong> {company.totalRevenue ? `$${company.totalRevenue.toLocaleString()}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Gross Profits:</strong> {company.grossProfits ? `$${company.grossProfits.toLocaleString()}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>EBITDA:</strong> {company.ebitda ? `$${company.ebitda.toLocaleString()}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Operating Margins:</strong> {company.operatingMargins ? `${(company.operatingMargins * 100).toFixed(2)}%` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Return on Assets:</strong> {company.returnOnAssets ? `${(company.returnOnAssets * 100).toFixed(2)}%` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Return on Equity:</strong> {company.returnOnEquity ? `${(company.returnOnEquity * 100).toFixed(2)}%` : 'N/A'}
          </div>
        </div>
        
        <h2>Stock Metrics</h2>
        <div className="info-grid">
          <div className="info-item">
            <strong>Current Price:</strong> {company.currentPrice ? `$${company.currentPrice.toFixed(2)}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Target High Price:</strong> {company.targetHighPrice ? `$${company.targetHighPrice.toFixed(2)}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Target Low Price:</strong> {company.targetLowPrice ? `$${company.targetLowPrice.toFixed(2)}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Target Mean Price:</strong> {company.targetMeanPrice ? `$${company.targetMeanPrice.toFixed(2)}` : 'N/A'}
          </div>
          <div className="info-item">
            <strong>Recommendation Mean:</strong> {company.recommendationMean ? company.recommendationMean.toFixed(2) : 'N/A'}
          </div>
        </div>
      </div>
      
      <div className="analysis-section">
        <h2>Analysis</h2>
        
        {analyzing && (
          <div className="analysis-status">
            <h3>Analysis in Progress</h3>
            <p>Analyzing SEC filings. This may take several minutes...</p>
          </div>
        )}
        
        {!analyzing && latestAnalysis ? (
          <div className="analysis-result">
            <h3>Latest Analysis ({new Date(latestAnalysis.analysis_date).toLocaleDateString()})</h3>
            <div className="analysis-details">
              <div className="analysis-item">
                <strong>Stock Expected to Go Up:</strong> {latestAnalysis.analysis_result.stock_expected_to_go_up ? 'Yes' : 'No'}
              </div>
              <div className="analysis-item">
                <strong>Good Buy:</strong> {latestAnalysis.analysis_result.is_good_buy ? 'Yes' : 'No'}
              </div>
              <div className="analysis-item">
                <strong>Reasoning:</strong> {latestAnalysis.analysis_result.reasoning}
              </div>
            </div>
          </div>
        ) : !analyzing && (
          <div className="no-analysis">
            <p>No analysis performed yet.</p>
          </div>
        )}
        
        <button 
          className="analyze-button" 
          onClick={handleAnalyze} 
          disabled={analyzing}
        >
          {analyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
    </div>
  );
};

export default CompanyDetail; 