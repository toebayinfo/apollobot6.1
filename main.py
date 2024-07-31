import os
from dotenv import load_dotenv
import xi.sdk.resellers
from xi.sdk.resellers.rest import ApiException
from pprint import pprint

# Load environment variables
load_dotenv()

# Configure the SDK
configuration = xi.sdk.resellers.Configuration(
    host="https://api.ingrammicro.com:443"
)

# Create an API client
with xi.sdk.resellers.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = xi.sdk.resellers.AccesstokenApi(api_client)
    
    # Set up your credentials
    grant_type = 'client_credentials'
    client_id = os.getenv('INGRAM_CLIENT_ID')
    client_secret = os.getenv('INGRAM_CLIENT_SECRET')

    try:
        # Get access token
        api_response = api_instance.get_accesstoken(grant_type, client_id, client_secret)
        print("Access token response:")
        pprint(api_response)
    except ApiException as e:
        print(f"Exception when calling AccesstokenApi->get_accesstoken: {e}\n")