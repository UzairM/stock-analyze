import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const location = useLocation();
  
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">Biotech Analysis Tool</Link>
      </div>
      <div className="navbar-menu">
        <Link 
          to="/" 
          className={`navbar-item ${location.pathname === '/' ? 'active' : ''}`}
        >
          Companies
        </Link>
        <Link 
          to="/upload" 
          className={`navbar-item ${location.pathname === '/upload' ? 'active' : ''}`}
        >
          Upload CSV
        </Link>
      </div>
    </nav>
  );
};

export default Navbar; 