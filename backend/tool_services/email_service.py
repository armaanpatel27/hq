import os.path
import base64
from email.mime.text import MIMEText
from typing import List, Optional
from email.message import EmailMessage
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

load_dotenv()

class EmailService:
    def __init__(self, credentials_path: str = os.getenv("CREDENTIALS_PATH"), token_path: str = "token.json"):
        """Initialize the email service.
        
        Args:
            credentials_path: Path to the Google OAuth credentials file
            token_path: Path to store/load the OAuth token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        with open(os.getenv("CONTACTS_PATH"), "r") as f:
          self.contacts = json.load(f)
        self._authenticate() 

    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> dict:
        """Send an email using Gmail API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (can be HTML)
            cc: List of CC recipients
            bcc: List of BCC recipients
            
        Returns:
            dict: Response from Gmail API
        """
        try:
            contact_email = self.get_contact_email(to)
            bcc_emails = self.get_list_emails(bcc)
            cc_emails = self.get_list_emails(cc)
            message = EmailMessage()
            message.set_content(body)
            message["to"] = contact_email
            message["subject"] = subject.strip()
            if cc:
                message["cc"] = ", ".join(cc_emails)
            if bcc:
                message["bcc"] = ", ".join(bcc_emails)

            # Encode message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create message
            created_messages = {"raw": encoded_message}

            
            # Send message
            sent_message = self.service.users().messages().send(
                userId="me", body=created_messages
            ).execute()
            
            return {
                "status": "success",
                "message_id": sent_message["id"],
                "thread_id": sent_message["threadId"]
            }

        except HttpError as error:
            return {
                "status": "error",
                "error": str(error)
            }
        
    def get_contact_email(self, input) -> str:
      return self.contacts[input.lower()]
    
    def get_list_emails(self, input) -> str:
      output = []
      if not input:
        return None
      else:
        for email in input:
          output.append(self.contacts[email])
      return output



