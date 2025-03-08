from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://mongodb:27017')
db = client['biotech_analysis_db']

# Get the first company
company = db.companies.find_one()

if company:
    company_id = str(company["_id"])
    print(f"Company ID: {company_id}")
    print(f"Company Name: {company.get('name', 'Unknown')}")
else:
    print("No companies found in the database.") 