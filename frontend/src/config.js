// API configuration
// Use environment variable with fallback to localhost
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

console.log('Using API URL:', API_URL);

export { API_URL }; 