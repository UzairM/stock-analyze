Below is the Product Requirements Document (PRD) for the software program as specified in your query. This PRD outlines the features, technical requirements, and data model for a web application designed to manage and analyze biotech companies using React, Python, and MongoDB.

---

# Product Requirements Document (PRD) for Biotech Company Analysis Tool

## 1. Overview

The Biotech Company Analysis Tool is a web application designed to assist users in exploring and analyzing biotech companies based on their financial filings. The application provides a list of biotech companies, detailed company information, and an analysis feature that leverages a Large Language Model (LLM) to evaluate SEC filings and predict stock performance. Additionally, it includes functionality to upload company data via CSV files, making it easy to populate and manage the database.

## 2. Objectives

- Enable users to view a list of biotech companies and access detailed information about each one.
- Allow users to analyze a company's recent SEC filings (8-K, 10-K, 10-Q) using an LLM to gain insights into stock performance and investment potential.
- Save analysis results for future reference and provide the option to rerun analyses.
- Offer a mechanism to upload a CSV file containing company data to populate or update the database.
- Deliver a responsive and intuitive user experience built with a modern software stack.

## 3. Features and Requirements

### 3.1 Company List Page

- **Description**: A page displaying a list of biotech companies by name.
- **Requirements**:
  - Display company names in a clickable list format.
  - Clicking a company name navigates to the Company Detail Page.
  - If no companies are present in the database, display a message: "No companies added yet. Please upload a CSV to add companies."

### 3.2 Company Detail Page

- **Description**: A page showing detailed information about a selected biotech company and its analysis results.
- **Requirements**:
  - Display company information based on the CSV headers (e.g., ticker, name, sector, industry, country, exchange, market_cap, employees, incorporation_date, website, totalRevenue, grossProfits, ebitda, operatingMargins, returnOnAssets, returnOnEquity, currentPrice, targetHighPrice, targetLowPrice, targetMeanPrice, recommendationMean).
  - Show the most recent analysis result (if available), including:
    - Date of the analysis.
    - LLM response details (stock performance prediction, timing, buy recommendation, and reasoning).
  - Include an "Analyze" button to initiate a new analysis.
  - If no analysis exists, display: "No analysis performed yet" alongside the "Analyze" button.

### 3.3 Analysis Functionality

- **Description**: A feature to download and analyze a company's SEC filings using an LLM.
- **Requirements**:
  - **Trigger**: Clicking the "Analyze" button on the Company Detail Page.
  - **Process**:
    - The frontend sends a request to the backend to start the analysis.
    - The backend performs the following asynchronously:
      - Retrieves the company's CIK (Central Index Key) from the database (looked up via ticker during CSV upload).
      - Downloads the company's 8-K, 10-K, and 10-Q filings from the SEC EDGAR database for the past 12 months.
      - Extracts the text content of these filings.
      - Sends the text to an LLM with a prompt such as:  
        _"Analyze the following SEC filings for information related to NDAs, positive phase 3 trials, and signs of upcoming FDA approval. Determine if the stock is expected to go up soon, by when, and if it’s a good buy or not. Provide reasoning for your conclusion."_
      - Receives a structured LLM response in JSON format, e.g.:  
        ```json
        {
          "stock_expected_to_go_up": true,
          "expected_by_date": "2023-12-31",
          "is_good_buy": true,
          "reasoning": "Based on positive phase 3 trial results and upcoming FDA approval, the stock is likely to increase."
        }
        ```
      - Saves the analysis result in the database, linked to the company.
    - The frontend polls the backend periodically using a task ID to check the analysis status and displays the result once completed.
  - **Output**: The analysis result includes:
    - Whether the stock is expected to go up soon (true/false).
    - By when (date).
    - If it’s a good buy (true/false).
    - Reasoning behind the conclusion.
  - **User Experience**: Display a loading indicator during analysis and update the page with the result upon completion.

### 3.4 Upload Page

- **Description**: A page allowing users to upload a CSV file to add or update companies in the database.
- **Requirements**:
  - Provide a file input field and an upload button.
  - Accept CSV files with the following headers:  
    `ticker, name, sector, industry, country, exchange, market_cap, employees, incorporation_date, website, totalRevenue, grossProfits, ebitda, operatingMargins, returnOnAssets, returnOnEquity, currentPrice, targetHighPrice, targetLowPrice, targetMeanPrice, recommendationMean`
  - **Processing**:
    - The frontend sends the CSV file to the backend.
    - The backend:
      - Parses the CSV file.
      - For each row, uses the ticker to look up the CIK from the SEC’s company tickers JSON (e.g., https://www.sec.gov/files/company_tickers.json).
      - Inserts a new company into the database if the ticker doesn’t exist; updates the existing company if it does.
      - Logs errors for rows with missing CIKs or invalid data and continues processing the remaining rows.
    - Returns a success message to the frontend (e.g., "Upload successful").
  - **Validation**: Ensure the CSV includes all required headers; skip rows with missing mandatory fields (e.g., ticker, name).

## 4. Technical Requirements

### 4.1 Frontend

- **Technology**: React.
- **Components**:
  - **Company List**: Renders the list of companies.
  - **Company Detail**: Displays company info and analysis results, handles the "Analyze" button.
  - **Upload CSV**: Manages file selection and submission.
- **Functionality**:
  - Handle navigation between pages.
  - Send API requests to the backend for analysis and CSV uploads.
  - Poll the backend for analysis results and update the UI accordingly.

### 4.2 Backend

- **Technology**: Python (FastAPI).
- **Responsibilities**:
  - Serve API endpoints for the frontend (e.g., list companies, get company details, start analysis, upload CSV).
  - Interact with MongoDB for data storage and retrieval.
  - Fetch SEC filings using the SEC EDGAR API or a library like `sec-edgar-api`.
  - Call an external LLM API (e.g., OpenAI) to analyze filings.
  - Manage asynchronous tasks (e.g., using Celery) for analysis processing.
- **Dependencies**:
  - Library to fetch SEC company tickers JSON and map tickers to CIKs.
  - HTTP client for SEC EDGAR and LLM API calls.

### 4.3 Database

- **Technology**: MongoDB.
- **Collections**:
  - **Companies**: Stores company data.
  - **Analyses**: Stores analysis results linked to companies.

## 5. Data Model

### 5.1 Companies Collection

- **Schema**:
  ```json
  {
    "_id": "ObjectId",
    "cik": "String", // SEC Central Index Key
    "ticker": "String",
    "name": "String",
    "sector": "String",
    "industry": "String",
    "country": "String",
    "exchange": "String",
    "market_cap": "Number",
    "employees": "Number",
    "incorporation_date": "Date",
    "website": "String",
    "totalRevenue": "Number",
    "grossProfits": "Number",
    "ebitda": "Number",
    "operatingMargins": "Number",
    "returnOnAssets": "Number",
    "returnOnEquity": "Number",
    "currentPrice": "Number",
    "targetHighPrice": "Number",
    "targetLowPrice": "Number",
    "targetMeanPrice": "Number",
    "recommendationMean": "Number"
  }
  ```

### 5.2 Analyses Collection

- **Schema**:
  ```json
  {
    "_id": "ObjectId",
    "company_id": "ObjectId", // Reference to Companies collection
    "analysis_date": "Date",
    "filings_analyzed": ["String"], // e.g., ["8-K", "10-K", "10-Q"]
    "analysis_result": {
      "stock_expected_to_go_up": "Boolean",
      "expected_by_date": "Date",
      "is_good_buy": "Boolean",
      "reasoning": "String"
    }
  }
  ```

## 6. Non-Functional Requirements

- **Performance**: Analysis tasks should be processed asynchronously to prevent UI blocking; aim for reasonable response times despite external API dependencies.
- **Usability**: The interface should be intuitive, with clear feedback during uploads and analyses (e.g., loading indicators, success/error messages).
- **Reliability**: Handle errors gracefully (e.g., missing CIKs, invalid CSV data) and log issues for debugging.
- **Security**: Secure API communications (e.g., HTTPS) and protect sensitive data like API keys for the LLM and SEC EDGAR.

## 7. Future Considerations

- Add user authentication to restrict access or manage individual user data.
- Implement filtering options on the Company List Page (e.g., by sector or market cap).
- Display a history of past analyses on the Company Detail Page.
- Optimize LLM input handling for large filing texts (e.g., summarization or chunking).
- Cache frequent analyses to reduce costs and improve performance.

---

This PRD provides a comprehensive blueprint for developing the Biotech Company Analysis Tool, ensuring it meets your requirements for viewing, analyzing, and managing biotech company data with the specified software stack (React, Python, MongoDB).