# Phase 3: Frontend Integration & Company Pages

1. **Set Up React Routing**  
  - [ ] Install `react-router-dom` if not done yet  
  - [ ] Create routes:  
    - `/` for Company List  
    - `/company/:id` for Company Detail  
    - `/upload` for CSV Upload  

2. **Company List Page**  
  - [ ] Fetch `/companies` from backend  
  - [ ] Display clickable list of company names  
  - [ ] If empty, show “No companies added yet...” message  

3. **Company Detail Page**  
  - [ ] Fetch single company data from backend  
  - [ ] Display all relevant fields (ticker, name, etc.)  
  - [ ] Show recent analysis result if available  
  - [ ] Add “Analyze” button calling the placeholder analysis endpoint  

4. **Integration & UI Checks**  
  - [ ] Confirm data flows from DB to React pages  
  - [ ] Style the pages minimally for clarity  