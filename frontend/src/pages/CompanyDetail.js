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
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);

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

  // Effect to handle polling for analysis status
  useEffect(() => {
    // Clean up polling interval when component unmounts
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const pollAnalysisStatus = async (taskId) => {
    try {
      const response = await axios.get(`${API_URL}/analyses/status/${taskId}`);
      setAnalysisStatus(response.data);
      
      // If the analysis is completed, stop polling and update analyses
      if (response.data.status === 'COMPLETED') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        
        setAnalyzing(false);
        
        if (response.data.analysis) {
          // Add the completed analysis to the analyses list
          setAnalyses(prevAnalyses => [response.data.analysis, ...prevAnalyses]);
        } else if (response.data.analysis_id) {
          // If we only get the analysis ID, fetch the complete analysis
          const analysisResponse = await axios.get(`${API_URL}/analyses/${response.data.analysis_id}`);
          setAnalyses(prevAnalyses => [analysisResponse.data, ...prevAnalyses]);
        }
      } else if (response.data.status === 'FAILED') {
        // If the analysis failed, stop polling and show error
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        
        setAnalyzing(false);
        setError(`Analysis failed: ${response.data.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error polling analysis status:', err);
      // Don't stop polling on error, it might be temporary
    }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      setError(null);
      setAnalysisStatus({ status: 'STARTING', message: 'Starting analysis...' });
      
      const response = await axios.post(`${API_URL}/analyses/`, {
        company_id: id,
        filings_analyzed: ['8-K', '10-K', '10-Q']
      });
      
      // If we get a task_id, set up polling
      if (response.data && response.data.task_id) {
        setAnalysisStatus({
          status: 'PENDING',
          task_id: response.data.task_id,
          message: response.data.message || 'Analysis in progress...'
        });
        
        // Start polling for status every 2 seconds
        const interval = setInterval(() => {
          pollAnalysisStatus(response.data.task_id);
        }, 2000);
        
        setPollingInterval(interval);
      } else {
        // If no task_id, treat as immediate completion
        setAnalyzing(false);
        // Add the new analysis to the analyses array if it's provided in the response
        if (response.data && response.data._id) {
          setAnalyses(prevAnalyses => [response.data, ...prevAnalyses]);
        }
      }
    } catch (err) {
      setError('Error performing analysis: ' + (err.response?.data?.detail || err.message));
      setAnalyzing(false);
      setAnalysisStatus(null);
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
        
        {analyzing && analysisStatus && (
          <div className="analysis-status">
            <h3>Analysis in Progress</h3>
            <p><strong>Status:</strong> {analysisStatus.status}</p>
            {analysisStatus.message && <p>{analysisStatus.message}</p>}
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
                <strong>Expected By:</strong> {latestAnalysis.analysis_result.expected_by_date ? new Date(latestAnalysis.analysis_result.expected_by_date).toLocaleDateString() : 'N/A'}
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