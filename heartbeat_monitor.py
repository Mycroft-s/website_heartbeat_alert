#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Website Heartbeat Monitor Script
Monitors https://c2smart.engineering.nyu.edu/ every 30 minutes
Sends email notifications via Gmail API if errors are detected

Usage:
1. Configure Gmail API credentials (see config.json)
2. Run: python heartbeat_monitor.py
3. Run in background: nohup python heartbeat_monitor.py > heartbeat.log 2>&1 &
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# Configuration constants
WEBSITE_URL = "https://c2smart.engineering.nyu.edu/"
CHECK_INTERVAL = 10 * 60  # 10 minutes (in seconds)
TIMEOUT = 30  # Request timeout (in seconds)
CONFIG_FILE = "heartbeat_config.json"
TOKEN_FILE = "gmail_token.pickle"
TOKEN_JSON_FILE = "gmail_token.json"
CREDENTIALS_FILE = "gmail_credentials.json"
LOG_FILE = "heartbeat_monitor.log"

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class HeartbeatMonitor:
    """Website heartbeat monitoring system"""
    
    def __init__(self, config_file=CONFIG_FILE):
        """Initialize monitor"""
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.gmail_service = None
        self.last_check_time = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 2  # Send email after 2 consecutive failures
        self.last_alert_sent = False  # Track if alert was already sent for current issue
        
    def load_config(self, config_file):
        """Load configuration file"""
        if not os.path.exists(config_file):
            # Create default configuration file
            default_config = {
                "recipient_email": ["your-email@example.com"],
                "sender_email": "your-email@gmail.com",
                "check_interval": CHECK_INTERVAL,
                "timeout": TIMEOUT,
                "max_consecutive_failures": 2
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"Created default config file: {config_file}")
            print("Please edit the config file and fill in correct email addresses and Gmail API credentials")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate required configuration
        required_keys = ['recipient_email', 'sender_email']
        for key in required_keys:
            if key not in config or not config[key]:
                raise ValueError(f"Please set {key} in the config file")
            # Special handling for recipient_email, support string or array format
            if key == 'recipient_email':
                if isinstance(config[key], str):
                    # If it's a string, check if it's the default value
                    if config[key] == "your-email@example.com":
                        raise ValueError(f"Please set {key} in the config file")
                elif isinstance(config[key], list):
                    # If it's an array, check if it's empty
                    if len(config[key]) == 0:
                        raise ValueError(f"Please set {key} in the config file with at least one email address")
                else:
                    raise ValueError(f"{key} must be a string or array format")
            elif config[key] == f"your-{key.split('_')[0]}@example.com":
                raise ValueError(f"Please set {key} in the config file")
        
        return config
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def authenticate_gmail(self):
        """Authenticate Gmail API - using same logic as test_gmail.py"""
        try:
            # Load token from JSON file
            if not os.path.exists(TOKEN_JSON_FILE):
                self.logger.error(f"Token file not found: {TOKEN_JSON_FILE}")
                self.logger.warning("Monitoring will continue but email alerts will not be sent")
                return False
            
            with open(TOKEN_JSON_FILE, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            self.logger.info("Successfully loaded token from JSON file")
            
            # Create credentials from saved token
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', SCOPES)
            )
            
            # Set expiry with proper timezone (same as test_gmail.py)
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
                    self.logger.info(f"Token expiry: {expiry_dt}")
                except Exception as e:
                    self.logger.warning(f"Could not parse expiry: {e}")
            
            # Check if token needs refresh (same as test_gmail.py)
            try:
                is_valid = creds.valid
            except (TypeError, AttributeError):
                # Timezone issue, assume needs refresh
                is_valid = False
            
            if not is_valid:
                self.logger.info("Token expired or invalid, refreshing...")
                creds.refresh(Request())
                self.logger.info("Token refreshed successfully")
                
                # Save refreshed token (same as test_gmail.py)
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
                self.logger.info("Refreshed token saved to file")
            else:
                self.logger.info("Token is valid, no refresh needed")
            
            # Build Gmail service (same as test_gmail.py)
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self.logger.info("Gmail API authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Gmail API authentication failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.logger.warning("Monitoring will continue but email alerts will not be sent")
            return False
    
    def save_token_to_json(self, creds):
        """Save Credentials object to JSON format"""
        try:
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'universe_domain': 'googleapis.com',
                'account': '',
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            with open(TOKEN_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            # Also save pickle format (backward compatibility)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
            self.logger.info("Token saved successfully")
        except Exception as e:
            self.logger.warning(f"Failed to save token: {e}")
    
    def send_email(self, subject, body):
        """Send email using Gmail API"""
        if not self.gmail_service:
            if not self.authenticate_gmail():
                self.logger.error("Cannot send email: Gmail API authentication failed")
                return False
        
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import base64
            
            message = MIMEMultipart()
            # Support multiple recipient emails (array format) or single email (string format)
            recipient_emails = self.config['recipient_email']
            if isinstance(recipient_emails, list):
                # If it's an array, join with commas
                message['to'] = ', '.join(recipient_emails)
            else:
                # If it's a string, use directly
                message['to'] = recipient_emails
            message['from'] = self.config['sender_email']
            message['subject'] = subject
            
            message.attach(MIMEText(body, 'plain', 'utf-8'))
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()).decode('utf-8')
            
            send_message = self.gmail_service.users().messages().send(
                userId='me', body={'raw': raw_message}).execute()
            
            self.logger.info(f"Email sent successfully: {send_message.get('id')}")
            return True
            
        except HttpError as error:
            self.logger.error(f"Error occurred while sending email: {error}")
            return False
        except Exception as e:
            self.logger.error(f"Unknown error occurred while sending email: {e}")
            return False
    
    def check_website(self):
        """Check if website is running normally"""
        try:
            response = requests.get(
                WEBSITE_URL,
                timeout=self.config.get('timeout', TIMEOUT),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                allow_redirects=True
            )
            
            # Check HTTP status code
            if response.status_code == 200:
                # Check if response content contains key elements (optional)
                if 'C2SMART' in response.text or len(response.text) > 1000:
                    return True, None
                else:
                    return False, f"Website response abnormal: incomplete content (status code: {response.status_code}, content length: {len(response.text)} bytes)"
            else:
                return False, f"Website returned error status code: {response.status_code} (URL: {WEBSITE_URL})"
                
        except requests.exceptions.Timeout as e:
            timeout_val = self.config.get('timeout', TIMEOUT)
            return False, f"Request timeout after {timeout_val} seconds. The server did not respond in time. (URL: {WEBSITE_URL})"
        except requests.exceptions.ConnectionError as e:
            error_detail = str(e)
            if "Name or service not known" in error_detail or "nodename nor servname provided" in error_detail:
                return False, f"DNS resolution failed: Unable to resolve domain name for {WEBSITE_URL}. The domain may not exist or DNS server is unreachable."
            elif "Connection refused" in error_detail:
                return False, f"Connection refused: The server at {WEBSITE_URL} is not accepting connections. The server may be down or the port is blocked."
            else:
                return False, f"Connection error: Unable to connect to server at {WEBSITE_URL}. Details: {error_detail}"
        except requests.exceptions.SSLError as e:
            return False, f"SSL/TLS error: Certificate verification failed or SSL handshake error. Details: {str(e)}"
        except requests.exceptions.TooManyRedirects as e:
            return False, f"Too many redirects: The website redirected too many times. This may indicate a redirect loop. (URL: {WEBSITE_URL})"
        except requests.exceptions.RequestException as e:
            return False, f"Request exception: {type(e).__name__} - {str(e)} (URL: {WEBSITE_URL})"
        except Exception as e:
            return False, f"Unknown error: {type(e).__name__} - {str(e)} (URL: {WEBSITE_URL})"
    
    def run_check(self):
        """Execute one check"""
        self.last_check_time = datetime.now()
        self.logger.info(f"Starting website check: {WEBSITE_URL}")
        
        is_healthy, error_message = self.check_website()
        
        if is_healthy:
            # Website recovered, reset failure tracking
            if self.consecutive_failures > 0:
                self.logger.info(f"✓ Website recovered after {self.consecutive_failures} failures")
            self.consecutive_failures = 0
            self.last_alert_sent = False  # Reset alert flag when website recovers
            self.logger.info("✓ Website is running normally")
        else:
            self.consecutive_failures += 1
            self.logger.warning(f"✗ Website check failed ({self.consecutive_failures} times): {error_message}")
            
            # If consecutive failures reach threshold, send email (only once per issue)
            max_failures = self.config.get('max_consecutive_failures', self.max_consecutive_failures)
            if self.consecutive_failures >= max_failures and not self.last_alert_sent:
                self.send_alert_email(error_message)
                self.last_alert_sent = True  # Mark that alert was sent for this issue
        
        return is_healthy
    
    def send_alert_email(self, error_message):
        """Send alert email with detailed error information"""
        subject = f"⚠️ Website Monitoring Alert: {WEBSITE_URL}"
        
        # Get additional context
        consecutive_failures = self.consecutive_failures
        check_interval_min = self.config.get('check_interval', CHECK_INTERVAL) / 60
        
        body = f"""
Website Heartbeat Monitoring Alert

═══════════════════════════════════════════════════════════
ALERT DETAILS
═══════════════════════════════════════════════════════════

Check Time: {self.last_check_time.strftime('%Y-%m-%d %H:%M:%S')}
Website URL: {WEBSITE_URL}
Consecutive Failures: {consecutive_failures} times
Check Interval: {check_interval_min} minutes

═══════════════════════════════════════════════════════════
ERROR INFORMATION
═══════════════════════════════════════════════════════════

{error_message}

═══════════════════════════════════════════════════════════
RECOMMENDED ACTIONS
═══════════════════════════════════════════════════════════

1. Check if the website is accessible from your browser
2. Verify the server is running and responding
3. Check network connectivity and DNS resolution
4. Review server logs for any error messages
5. Verify SSL certificate validity (if HTTPS)

═══════════════════════════════════════════════════════════

This is an automated alert from the Website Heartbeat Monitoring System.
The system will continue monitoring and will send another alert if the issue persists.

---
Monitoring System Status: Active
Next Check: Approximately {check_interval_min} minutes from now
"""
        
        self.logger.info("Sending alert email...")
        if self.send_email(subject, body):
            self.logger.info("Alert email sent successfully")
        else:
            self.logger.error("Failed to send alert email")
    
    def run(self):
        """Run monitoring loop"""
        self.logger.info("=" * 60)
        self.logger.info("Website Heartbeat Monitoring System Started")
        self.logger.info(f"Monitoring Website: {WEBSITE_URL}")
        self.logger.info(f"Check Interval: {self.config.get('check_interval', CHECK_INTERVAL) / 60} minutes")
        # Format recipient emails for display
        recipient_emails = self.config['recipient_email']
        if isinstance(recipient_emails, list):
            recipient_str = ', '.join(recipient_emails)
        else:
            recipient_str = recipient_emails
        self.logger.info(f"Recipient Emails: {recipient_str}")
        self.logger.info("=" * 60)
        
        # Initialize Gmail API (not mandatory, can continue running if it fails)
        self.authenticate_gmail()
        
        # Run check immediately on startup
        self.run_check()
        
        # Main loop
        check_interval = self.config.get('check_interval', CHECK_INTERVAL)
        
        try:
            while True:
                time.sleep(check_interval)
                self.run_check()
        except KeyboardInterrupt:
            self.logger.info("Received stop signal, exiting...")
        except Exception as e:
            self.logger.error(f"Monitoring system error: {e}", exc_info=True)
            # Send error notification
            try:
                subject = f"❌ Monitoring System Error: {WEBSITE_URL}"
                body = f"""
Monitoring System Error

Error Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Error Message: {str(e)}

---
This email is automatically sent by the Website Heartbeat Monitoring System
"""
                self.send_email(subject, body)
            except:
                pass


def main():
    """Main function"""
    try:
        monitor = HeartbeatMonitor()
        monitor.run()
    except Exception as e:
        print(f"Failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

