import os
import json
import base64
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as OAuthCredentials

# Minimum required scopes for Docs updating and Gmail draft creation
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.compose'
]

def get_google_credentials():
    """
    Decodes the Base64 environment variable and returns the correct Google 
    Credentials object, supporting both Service Accounts and OAuth user tokens.
    """
    b64_creds = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not b64_creds:
        return None

    try:
        decoded_bytes = base64.b64decode(b64_creds)
        creds_info = json.loads(decoded_bytes)

        # Autodetect if it's an OAuth token.json or a Service Account JSON
        if "token" in creds_info and "client_id" in creds_info:
            # Ensure refresh_token key exists to satisfy google-auth library requirements
            if "refresh_token" not in creds_info:
                creds_info["refresh_token"] = ""
            return OAuthCredentials.from_authorized_user_info(creds_info, scopes=SCOPES)
        else:
            return ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
    except Exception as e:
        print(f"Auth error parsing Google credentials: {e}")
        return None
