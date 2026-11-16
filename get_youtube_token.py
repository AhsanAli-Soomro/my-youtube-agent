#!/usr/bin/env python3
"""
YouTube Data API v3 OAuth2 Token Generator
Interactive helper script to obtain a permanent OAuth2 Refresh Token for automated uploads.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_token():
    print("=" * 70)
    print("🎬 YouTube OAuth2 Refresh Token Setup Assistant")
    print("=" * 70)
    print("This script will help you generate your permanent YOUTUBE_REFRESH_TOKEN.")
    print("Prerequisites:")
    print(" 1. Go to Google Cloud Console (https://console.cloud.google.com/)")
    print(" 2. Enable 'YouTube Data API v3'")
    print(" 3. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'")
    print(" 4. Choose Application Type: 'Desktop app' (or 'Web application')")
    print(" 5. Copy your Client ID and Client Secret.")
    print("-" * 70)

    # Check for downloaded client_secret.json
    client_secret_files = list(Path(".").glob("client_secret*.json"))
    flow = None
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ Error: google-auth-oauthlib is not installed.")
        print("Please run: pip install google-auth-oauthlib")
        sys.exit(1)

    if client_secret_files:
        secret_file = client_secret_files[0]
        print(f"📄 Found OAuth client file: {secret_file}")
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
        # Extract client_id and secret from JSON
        with open(secret_file) as f:
            data = json.load(f)
            key_data = data.get("installed") or data.get("web") or {}
            client_id = key_data.get("client_id", client_id)
            client_secret = key_data.get("client_secret", client_secret)
    else:
        if not client_id:
            client_id = input("Enter your YOUTUBE_CLIENT_ID: ").strip()
        else:
            print(f"Using YOUTUBE_CLIENT_ID from .env: {client_id[:20]}...")

        if not client_secret:
            client_secret = input("Enter your YOUTUBE_CLIENT_SECRET: ").strip()
        else:
            print("Using YOUTUBE_CLIENT_SECRET from .env: [HIDDEN]")

        if not client_id or not client_secret:
            print("❌ Both Client ID and Client Secret are required. Aborting.")
            sys.exit(1)

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n🌐 Starting local authorization server...")
    print("A browser window will open automatically. Sign in with the YouTube channel account")
    print("and grant permission to manage your YouTube videos.")
    print("If browser doesn't open, follow the link displayed on screen.\n")

    try:
        # Run local server flow with prompt=consent to ensure a refresh_token is returned
        credentials = flow.run_local_server(
            port=8080,
            access_type="offline",
            prompt="consent",
        )
    except Exception as err:
        print(f"\n⚠️  Local server flow error: {err}")
        print("Trying console URL flow...")
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        print(f"\nVisit this URL in your browser:\n{auth_url}\n")
        code = input("Enter the authorization code from that page: ").strip()
        flow.fetch_token(code=code)
        credentials = flow.credentials

    refresh_token = credentials.refresh_token

    if not refresh_token:
        print("\n⚠️  No refresh token was returned.")
        print("Google only issues a refresh token the first time you grant consent, or when prompt='consent'.")
        print("Revoke app access at https://myaccount.google.com/permissions and run this script again.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ SUCCESS! Here are your credentials:")
    print("=" * 70)
    print(f"YOUTUBE_CLIENT_ID={client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={refresh_token}")
    print("=" * 70)

    # Offer to update .env automatically
    env_file = Path(".env")
    update_env = input("\nWould you like to write/update these in your .env file now? (y/n): ").strip().lower()
    if update_env in ["y", "yes"]:
        lines = []
        if env_file.is_file():
            with open(env_file, "r") as f:
                lines = f.readlines()

        keys_to_update = {
            "YOUTUBE_CLIENT_ID": client_id,
            "YOUTUBE_CLIENT_SECRET": client_secret,
            "YOUTUBE_REFRESH_TOKEN": refresh_token,
        }

        updated_keys = set()
        new_lines = []
        for line in lines:
            updated = False
            for k, v in keys_to_update.items():
                if line.startswith(f"{k}="):
                    new_lines.append(f"{k}={v}\n")
                    updated_keys.add(k)
                    updated = True
                    break
            if not updated:
                new_lines.append(line)

        for k, v in keys_to_update.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}\n")

        with open(env_file, "w") as f:
            f.writelines(new_lines)

        print("💾 .env updated successfully!")
    else:
        print("Copy the values above into your .env or GitHub Secrets manually.")


if __name__ == "__main__":
    get_token()
