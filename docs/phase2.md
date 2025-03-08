# Phase 2: Basic Endpoints & Data Model

1. **Create MongoDB Models**  
  - [x] Define Companies collection structure in FastAPI  
  - [x] Define Analyses collection structure in FastAPI  

2. **Add Database Connection**  
  - [x] Install `motor` or `pymongo`  
  - [x] Configure a global DB client in `backend/main.py` or similar  

3. **Implement Basic CRUD**  
  - [x] Create endpoint to get all companies (GET `/companies`)  
  - [x] Create endpoint to get a single company by ID/ticker (GET `/companies/{id}`)  
  - [x] Create endpoint to add or update companies (POST `/companies`)  

4. **Test the Endpoints**  
  - [x] Use a simple client (like `requests` or `curl`) to confirm status 200  
  - [x] Verify DB insertion and retrieval  

5. **Stub Out Analyses**  
  - [x] Create a placeholder endpoint to receive analysis requests  
  - [x] No real LLM call yet—just return a mock response  