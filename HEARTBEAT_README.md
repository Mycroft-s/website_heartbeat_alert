# Website Heartbeat Monitoring System

This is a Python script for monitoring the operational status of the https://c2smart.engineering.nyu.edu/ website. It automatically checks the website every 30 minutes and sends email notifications via Gmail API if any anomalies are detected.

## Features

- ✅ Automatically checks website status every 30 minutes
- ✅ Supports background execution
- ✅ Sends email notifications using Gmail API
- ✅ Sends alerts only after multiple consecutive failures (to avoid frequent emails)
- ✅ Detailed logging
- ✅ Automatic retry and error handling

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements_heartbeat.txt
```

### 2. Configure Gmail API

#### Step 1: Create Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing project
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click Enable

#### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. Select "Desktop app" as the application type
4. Download the JSON credentials file
5. Rename the downloaded file to `gmail_credentials.json` and place it in the same directory as the script

#### Step 3: Configure Email Addresses

Edit the `heartbeat_config.json` file:

```json
{
  "recipient_email": "Email address to receive alerts",
  "sender_email": "Gmail address for sending emails (must match OAuth credentials)",
  "check_interval": 1800,
  "timeout": 30,
  "max_consecutive_failures": 3
}
```

**Important Notes:**
- `sender_email` must be the Gmail account used to create the OAuth credentials
- `recipient_email` can be any email address
- `check_interval` is the check interval in seconds, 1800 = 30 minutes
- `max_consecutive_failures` is the number of consecutive failures before sending an email

### 3. First Run Authentication

When running the script for the first time, it will automatically open a browser for OAuth authentication:

```bash
python heartbeat_monitor.py
```

1. The browser will automatically open the Google login page
2. Log in with the same Gmail account as `sender_email`
3. Authorize the application to access Gmail
4. Authentication information will be saved in the `gmail_token.pickle` file

## Usage

### Foreground Execution

```bash
python heartbeat_monitor.py
```

### Background Execution (Recommended)

```bash
# Run in background using nohup
nohup python heartbeat_monitor.py > heartbeat.log 2>&1 &

# Check process
ps aux | grep heartbeat_monitor

# View logs
tail -f heartbeat_monitor.log
```

### Stop Monitoring

```bash
# Find process ID
ps aux | grep heartbeat_monitor

# Stop process
kill <process_id>
```

Or use `Ctrl+C` (if running in foreground)

## File Description

- `heartbeat_monitor.py` - Main monitoring script
- `heartbeat_config.json` - Configuration file
- `gmail_credentials.json` - Gmail API credentials (need to download from Google Cloud)
- `gmail_token.pickle` - OAuth authentication token (automatically generated)
- `heartbeat_monitor.log` - Runtime logs
- `requirements_heartbeat.txt` - Python dependencies

## Logging

The script records the following information:
- Time and result of each check
- Website status (normal/abnormal)
- Email sending status
- Error messages

Log file: `heartbeat_monitor.log`

## Troubleshooting

### 1. Gmail API Authentication Failure

- Ensure `gmail_credentials.json` file exists and is correct
- Ensure `sender_email` matches the OAuth credentials account
- Delete `gmail_token.pickle` and re-authenticate

### 2. Email Sending Failure

- Check if Gmail API is enabled
- Check if OAuth credentials are valid
- View log file for detailed errors

### 3. False Website Detection Alerts

- Adjust `timeout` parameter to increase timeout duration
- Adjust `max_consecutive_failures` to reduce false positives

## Important Notes

1. **Gmail API Quota Limits**: Free accounts have daily email sending limits. Please set the check frequency appropriately.
2. **Security**: Do not commit `gmail_credentials.json` and `gmail_token.pickle` to version control systems.
3. **Network Requirements**: Ensure the server running the script can access the target website and Gmail API.

## Custom Configuration

You can adjust the following parameters in `heartbeat_config.json`:

- `check_interval`: Check interval in seconds, default 1800 (30 minutes)
- `timeout`: Request timeout in seconds, default 30
- `max_consecutive_failures`: Number of consecutive failures before sending email, default 3

