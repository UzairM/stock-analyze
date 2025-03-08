import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config';

const CompanyList = () => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_URL}/companies`);
        setCompanies(response.data);
        setLoading(false);
      } catch (err) {
        setError('Error fetching companies: ' + err.message);
        setLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  if (loading) {
    return <div>Loading companies...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="company-list">
      <h1>Biotech Companies</h1>
      {companies.length === 0 ? (
        <div className="no-companies">
          <p>No companies added yet. Please upload a CSV to add companies.</p>
          <Link to="/upload" className="upload-link">Upload CSV</Link>
        </div>
      ) : (
        <ul>
          {companies.map((company) => (
            <li key={company._id}>
              <Link to={`/company/${company._id}`}>
                {company.name} ({company.ticker})
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default CompanyList; 