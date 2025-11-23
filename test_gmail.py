#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail发送功能测试脚本
验证使用已保存的token发送邮件，无需重复OAuth认证

Usage:
    python3 test_gmail.py
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration constants
CONFIG_FILE = "heartbeat_config.json"
TOKEN_JSON_FILE = "gmail_token.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def setup_logging():
    """Setup logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)


def load_config():
    """Load configuration file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Error: Config file not found {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config


def load_and_authenticate(logger):
    """Load saved token and authenticate (no OAuth)"""
    if not os.path.exists(TOKEN_JSON_FILE):
        logger.error(f"❌ Token file not found: {TOKEN_JSON_FILE}")
        logger.error("Please run OAuth authentication first")
        return None
    
    try:
        # Load token from JSON file
        with open(TOKEN_JSON_FILE, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
        
        logger.info("✓ Loaded token from file")
        
        # Create credentials from saved token
        creds = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', SCOPES)
        )
        
        # Set expiry with proper timezone
        if 'expiry' in token_data and token_data['expiry']:
            try:
                expiry_str = token_data['expiry']
                if expiry_str.endswith('Z'):
                    expiry_str = expiry_str[:-1] + '+00:00'
                expiry_dt = datetime.fromisoformat(expiry_str)
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                else:
                    expiry_dt = expiry_dt.astimezone(timezone.utc)
                creds.expiry = expiry_dt
                logger.info(f"Token expiry: {expiry_dt}")
            except Exception as e:
                logger.warning(f"Could not parse expiry: {e}")
        
        # Check if token needs refresh
        try:
            is_valid = creds.valid
        except (TypeError, AttributeError):
            # Timezone issue, assume needs refresh
            is_valid = False
        
        if not is_valid:
            logger.info("Token expired or invalid, refreshing...")
            creds.refresh(Request())
            logger.info("✓ Token refreshed successfully")
            
            # Save refreshed token
            expiry_str = None
            if creds.expiry:
                expiry_dt = creds.expiry.astimezone(timezone.utc) if creds.expiry.tzinfo else creds.expiry.replace(tzinfo=timezone.utc)
                expiry_str = expiry_dt.isoformat().replace('+00:00', 'Z')
            
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'universe_domain': 'googleapis.com',
                'account': '',
                'expiry': expiry_str
            }
            
            with open(TOKEN_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            logger.info("Refreshed token saved to file")
        else:
            logger.info("✓ Token is valid, no refresh needed")
        
        # Build Gmail service
        gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("✓ Gmail API service created successfully")
        
        return gmail_service
        
    except Exception as e:
        logger.error(f"❌ Failed to load/authenticate: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def send_test_email(gmail_service, config, logger):
    """Send test email"""
    try:
        # Prepare recipients
        recipient_emails = config['recipient_email']
        if isinstance(recipient_emails, list):
            recipient_str = ', '.join(recipient_emails)
        else:
            recipient_str = recipient_emails
        
        # Create email
        message = MIMEMultipart()
        message['to'] = recipient_str
        message['from'] = config['sender_email']
        message['subject'] = '✅ Gmail Test - No OAuth Required'
        
        # Email body
        test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        body = f"""
This is a test email sent using saved Gmail API token.

Test Time: {test_time}
Sender Email: {config['sender_email']}
Recipient Email(s): {recipient_str}

✅ SUCCESS: This email was sent WITHOUT opening a browser for OAuth authentication!
The system successfully used the saved token to send this email.

This proves that:
1. Token loading works correctly
2. Token refresh works automatically (if needed)
3. No repeated OAuth authentication is required

---
Gmail API Test Script
"""
        
        message.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Encode and send
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()).decode('utf-8')
        
        logger.info("Sending test email...")
        send_message = gmail_service.users().messages().send(
            userId='me', body={'raw': raw_message}).execute()
        
        message_id = send_message.get('id')
        logger.info(f"✓ Email sent successfully!")
        logger.info(f"  Email ID: {message_id}")
        logger.info(f"  From: {config['sender_email']}")
        logger.info(f"  To: {recipient_str}")
        
        return True
        
    except HttpError as error:
        logger.error(f"❌ HTTP error occurred while sending email: {error}")
        return False
    except Exception as e:
        logger.error(f"❌ Error occurred while sending email: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main function"""
    print("=" * 70)
    print("Gmail API Test - No OAuth Authentication Required")
    print("=" * 70)
    print()
    print("This script demonstrates that:")
    print("  1. Saved token can be loaded and used")
    print("  2. Token refresh works automatically")
    print("  3. No browser OAuth is needed for subsequent runs")
    print()
    print("=" * 70)
    print()
    
    logger = setup_logging()
    
    # Load configuration
    logger.info("Loading configuration...")
    try:
        config = load_config()
        logger.info("✓ Configuration loaded")
        logger.info(f"  Sender: {config['sender_email']}")
        recipient_emails = config['recipient_email']
        if isinstance(recipient_emails, list):
            logger.info(f"  Recipients: {', '.join(recipient_emails)}")
        else:
            logger.info(f"  Recipient: {recipient_emails}")
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        sys.exit(1)
    
    print()
    
    # Load token and authenticate (NO OAuth)
    logger.info("Loading saved token (NO OAuth authentication)...")
    gmail_service = load_and_authenticate(logger)
    
    if not gmail_service:
        logger.error("❌ Failed to authenticate, cannot send email")
        logger.error("Hint: Make sure gmail_token.json exists and is valid")
        sys.exit(1)
    
    print()
    
    # Send test email
    logger.info("Preparing to send test email...")
    success = send_test_email(gmail_service, config, logger)
    
    print()
    print("=" * 70)
    if success:
        print("✅ TEST PASSED!")
        print()
        print("The email was sent successfully WITHOUT opening a browser!")
        print("This proves that:")
        print("  ✓ Token loading works")
        print("  ✓ Token refresh works (if needed)")
        print("  ✓ No repeated OAuth authentication required")
        print()
        print("Please check your inbox to confirm receipt.")
    else:
        print("❌ TEST FAILED!")
        print("Please check the error messages above.")
    print("=" * 70)


if __name__ == "__main__":
    main()

