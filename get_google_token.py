import json
import base64
import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scopes required (Docs + Gmail)
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.compose'
]

def main():
    if not os.path.exists("client_secret.json"):
        print("❌ Error: You need to create a file called 'client_secret.json' in this folder.")
        print("Please paste the raw JSON you downloaded from Google Cloud into 'client_secret.json'.")
        return

    print("🚀 Starting local authentication server...")
    print("A browser window should pop open asking you to sign into Google.\n")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", 
        SCOPES
    )

    # Boot up a local web server (Fixed port matches Google's redirect URI requirements)
    creds = flow.run_local_server(port=8080, prompt='consent')

    # We now have the token! Convert it to a dictionary
    creds_dict = json.loads(creds.to_json())

    # Safely convert to Base64
    base64_str = base64.b64encode(json.dumps(creds_dict).encode('utf-8')).decode('utf-8')

    print("\n✅ Authentication Successful!\n")
    
    # Automatically update the .env file
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
            
        with open(env_path, "w") as f:
            updated = False
            for line in lines:
                if line.startswith("GOOGLE_CREDENTIALS_BASE64="):
                    f.write(f'GOOGLE_CREDENTIALS_BASE64="{base64_str}"\n')
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f'\nGOOGLE_CREDENTIALS_BASE64="{base64_str}"\n')
                
        print("🎉 SUCCESS! Your new Token has been automatically saved into your .env file!")
        print("You don't need to copy and paste anything.")
    else:
        print(f"COPY this into your .env file as GOOGLE_CREDENTIALS_BASE64:\n{base64_str}")
        
    print("\n--------------------------------------------------------------------------------")

if __name__ == "__main__":
    main()
