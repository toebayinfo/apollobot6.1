import os
from dotenv import load_dotenv

load_dotenv()

class CONFIG:
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    SHAREPOINT_SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
    EXCEL_FILE_URL = os.getenv("EXCEL_FILE_URL")
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    INGRAM_CLIENT_ID = os.getenv("INGRAM_CLIENT_ID")
    INGRAM_CLIENT_SECRET = os.getenv("INGRAM_CLIENT_SECRET")

    MICROSOFT_APP_ID = os.getenv("MicrosoftAppId")
    MICROSOFT_APP_PASSWORD = os.getenv("MicrosoftAppPassword")
    
    WEBSITES_PORT = os.getenv("WEBSITES_PORT", 8000)  # Default to 8000 if not set
    PORT = os.getenv("PORT", 8000)  # Default to 8000 if not set
    
    
