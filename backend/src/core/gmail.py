"""
Google Gmail API client for MailMind AI.
Handles OAuth authentication and email fetching.
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict, Any

class GmailClient:
    def __init__(self, access_token: str, refresh_token: str, client_id: str, client_secret: str):
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token"
        )
        self.service = build("gmail", "v1", credentials=self.creds)

    def list_messages(self, user_id: str = "me", max_results: int = 10):
        try:
            results = self.service.users().messages().list(
                userId=user_id, maxResults=max_results
            ).execute()
            return results.get("messages", [])
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def get_message(self, message_id: str, user_id: str = "me"):
        try:
            return self.service.users().messages().get(
                userId=user_id, id=message_id, format="full"
            ).execute()
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
