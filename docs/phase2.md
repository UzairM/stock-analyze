# Phase 2: Basic Endpoints & Data Model

1. **Create MongoDB Models**  
  - [ ] Define Companies collection structure in FastAPI  
  - [ ] Define Analyses collection structure in FastAPI  

2. **Add Database Connection**  
  - [ ] Install `motor` or `pymongo`  
  - [ ] Configure a global DB client in `backend/main.py` or similar  

3. **Implement Basic CRUD**  
  - [ ] Create endpoint to get all companies (GET `/companies`)  
  - [ ] Create endpoint to get a single company by ID/ticker (GET `/companies/{id}`)  
  - [ ] Create endpoint to add or update companies (POST `/companies`)  

4. **Test the Endpoints**  
  - [ ] Use a simple client (like `requests` or `curl`) to confirm status 200  
  - [ ] Verify DB insertion and retrieval  

5. **Stub Out Analyses**  
  - [ ] Create a placeholder endpoint to receive analysis requests  
  - [ ] No real LLM call yet—just return a mock response  