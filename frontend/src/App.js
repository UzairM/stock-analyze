import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// Import components
import Navbar from './components/Navbar';

// Import pages
import CompanyList from './pages/CompanyList';
import CompanyDetail from './pages/CompanyDetail';
import Upload from './pages/Upload';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <main className="App-main">
          <Routes>
            <Route path="/" element={<CompanyList />} />
            <Route path="/company/:id" element={<CompanyDetail />} />
            <Route path="/upload" element={<Upload />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
