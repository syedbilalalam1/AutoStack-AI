import webbrowser
import time
from urllib.parse import urlencode

# Your Stack App credentials
CLIENT_ID = "30689"
REDIRECT_URI = "https://stackexchange.com/oauth/login_success"
SCOPE = "write_access no_expiry private_info"

# Construct the authorization URL
params = {
    'client_id': CLIENT_ID,
    'redirect_uri': REDIRECT_URI,
    'scope': SCOPE,
    'response_type': 'token'  # This is important for implicit flow
}

auth_url = f"https://stackoverflow.com/oauth/dialog?{urlencode(params)}"

print("Stack Exchange Token Generator (Simple)")
print("======================================")
print("\nFollow these steps:")
print("1. The browser will open with Stack Exchange authorization page")
print("2. Click 'Approve' to authorize the application")
print("3. Look at your browser's address bar")
print("4. Copy the access_token value from the URL")
print("\nThe URL will look like:")
print("https://stackexchange.com/oauth/login_success#access_token=YOUR_TOKEN_HERE&expires=...")
print("\nPress Enter to open the browser...")
input()

# Open the authorization URL
print(f"\nOpening: {auth_url}")
webbrowser.open(auth_url)

print("\nAfter approving, copy the access_token value from the URL")
print("Add ')) at the end of the token when adding it to your .env file") 