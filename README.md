# Biotech Stock Analysis

A full-stack application for analyzing biotech stocks using FastAPI, React, and MongoDB.

## Project Overview

This application provides tools for analyzing biotech stocks, including:
- Stock data visualization
- Company information tracking
- Sector analysis
- Custom watchlists

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Database**: MongoDB
- **Containerization**: Docker & Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- Node.js (for local development)
- MongoDB (for local development)

### Setup with Docker

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd biotech-stock-analysis
   ```

2. Start the application using Docker Compose:
   ```bash
   docker-compose up
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development Setup

#### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with the following content:
   ```
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=biotech_analysis_db
   ```

5. Run the database setup script:
   ```bash
   python db_setup.py
   ```

6. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

## Project Structure

```
biotech-stock-analysis/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── models/         # Pydantic models
│   │   ├── routes/         # API routes
│   │   ├── database/       # Database connection and queries
│   │   └── utils/          # Utility functions
│   ├── main.py             # FastAPI application entry point
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend Docker configuration
├── frontend/               # React frontend
│   ├── public/             # Static files
│   ├── src/                # React components and logic
│   ├── package.json        # Node.js dependencies
│   └── Dockerfile          # Frontend Docker configuration
├── docs/                   # Documentation
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # Project documentation
```

## API Endpoints

- `GET /`: Welcome message
- `GET /health`: Health check endpoint
- `GET /stocks/`: List all stocks
- `POST /stocks/`: Create a new stock
- `GET /stocks/{symbol}`: Get a specific stock
- `PUT /stocks/{symbol}`: Update a stock
- `DELETE /stocks/{symbol}`: Delete a stock

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 