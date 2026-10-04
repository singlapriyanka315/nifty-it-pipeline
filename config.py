import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/nifty_it")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./vector_db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")  # check console.groq.com if retired
REPORTS_DIR = "reports"

INDEX = {"name": "NIFTY IT", "symbol": "^CNXIT"}

# name -> Yahoo symbol, the name to search news for, and words a relevant headline must contain
STOCKS = {
    "TCS":           {"symbol": "TCS.NS",     "search": "Tata Consultancy Services", "keywords": ["tcs", "tata consultancy"]},
    "Infosys":       {"symbol": "INFY.NS",    "search": "Infosys",                   "keywords": ["infosys", "infy"]},
    "Wipro":         {"symbol": "WIPRO.NS",   "search": "Wipro",                     "keywords": ["wipro"]},
    "HCLTech":       {"symbol": "HCLTECH.NS", "search": "HCLTech",                   "keywords": ["hcl"]},
    "Tech Mahindra": {"symbol": "TECHM.NS",   "search": "Tech Mahindra",             "keywords": ["tech mahindra", "techm"]},
}
