# Phase 4: Analysis Logic, CSV Upload & Finalization

1. **Add Real Analysis**  
  - [ ] Integrate with SEC EDGAR API or `sec-edgar-api`  
  - [ ] Download and parse recent filings (8-K, 10-K, 10-Q)  
  - [ ] Send text to LLM (OpenAI or other)  
  - [ ] Save analysis result in `Analyses` collection  

2. **Asynchronous Tasks**  
  - [ ] Install and configure Celery or similar  
  - [ ] Kick off analysis job, return task ID  
  - [ ] Poll for status in frontend  

3. **Implement CSV Upload**  
  - [ ] Create an Upload page in React with file input  
  - [ ] Parse CSV in the backend, map tickers to CIK  
  - [ ] Insert or update company data  

4. **Final Testing & Cleanup**  
  - [ ] Verify final end-to-end workflow (upload -> list -> detail -> analyze)  
  - [ ] Conduct performance checks and correct slow processes  
  - [ ] Document usage, known issues, and next steps in `README.md`  