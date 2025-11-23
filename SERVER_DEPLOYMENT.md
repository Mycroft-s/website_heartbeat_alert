# Server Deployment Guide

## Quick Start

### Method 1: One-Click Setup Script (Recommended)

Run the following commands on the server:

```bash
# 1. Upload project files to server (using scp or other methods)
# 2. Navigate to project directory
cd /path/to/c2smarter_data

# 3. Run one-click setup script
bash setup_server.sh
```

The script will automatically:
- ✅ Check Python environment
- ✅ Install all dependencies
- ✅ Check required files
- ✅ Create default configuration file (if it doesn't exist)
- ✅ Set execution permissions

### Method 2: Manual Installation

If the one-click script cannot run, you can manually execute:

```bash
# 1. Check Python version (requires 3.7+)
python3 --version

# 2. Install dependencies
pip3 install -r requirements_heartbeat.txt

# Or use user installation (if no root privileges)
pip3 install --user -r requirements_heartbeat.txt
```

## File Preparation

The following files are required on the server:

### Required Files
- ✅ `heartbeat_monitor.py` - Main monitoring script
- ✅ `requirements_heartbeat.txt` - Dependency list
- ✅ `heartbeat_config.json` - Configuration file
- ✅ `gmail_credentials.json` - Gmail API credentials
- ✅ `gmail_token.json` - OAuth token (generated after first authentication)

### Optional Files
- `test_email.py` - Test script
- `setup_server.sh` - Setup script

## Gmail Token Configuration

### Method 1: Get Token on Local MacBook (Recommended)

1. Run the test script once on your local MacBook:
   ```bash
   python3 test_email.py
   ```

2. After completing OAuth authentication, the following files will be generated:
   - `gmail_token.json`
   - `gmail_token.pickle`

3. Copy these files to the server:
   ```bash
   scp gmail_token.json gmail_token.pickle user@server:/path/to/c2smarter_data/
   scp gmail_credentials.json user@server:/path/to/c2smarter_data/
   ```

### Method 2: Direct Authentication on Server

If the server has a graphical interface or can use SSH port forwarding:

```bash
# Run monitoring script, will automatically open browser for authentication
python3 heartbeat_monitor.py
```

If there's no graphical interface, you can use SSH port forwarding:

```bash
# Execute on local MacBook
ssh -L 8080:localhost:8080 user@server

# Then run script on server
python3 heartbeat_monitor.py
```

## Running Monitoring

### Foreground Execution (for testing)

```bash
python3 heartbeat_monitor.py
```

### Background Execution (for production)

```bash
# Run in background using nohup
nohup python3 heartbeat_monitor.py > heartbeat.log 2>&1 &

# Check process
ps aux | grep heartbeat_monitor

# View logs
tail -f heartbeat_monitor.log
```

### Using systemd (Recommended for production)

Create systemd service file `/etc/systemd/system/heartbeat-monitor.service`:

```ini
[Unit]
Description=Website Heartbeat Monitor
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/c2smarter_data
ExecStart=/usr/bin/python3 /path/to/c2smarter_data/heartbeat_monitor.py
Restart=always
RestartSec=10
StandardOutput=append:/path/to/c2smarter_data/heartbeat.log
StandardError=append:/path/to/c2smarter_data/heartbeat.log

[Install]
WantedBy=multi-user.target
```

Then start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable heartbeat-monitor
sudo systemctl start heartbeat-monitor

# Check status
sudo systemctl status heartbeat-monitor

# View logs
sudo journalctl -u heartbeat-monitor -f
```

## Common Issues

### 1. Python Version Issue

If the server Python version is too low:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3-pip

# CentOS/RHEL
sudo yum install python39 python39-pip
```

### 2. Permission Issue

If unable to install to system directory, use user installation:

```bash
pip3 install --user -r requirements_heartbeat.txt
```

### 3. Network Issue

If the server cannot access the internet, you need to:

1. Download all dependencies locally:
   ```bash
   pip3 download -r requirements_heartbeat.txt -d packages/
   ```

2. Upload the packages directory to the server

3. Install on the server:
   ```bash
   pip3 install --no-index --find-links=packages/ -r requirements_heartbeat.txt
   ```

### 4. Token Expiration

If the token expires, the script will automatically refresh. If refresh fails:

1. Delete old token files:
   ```bash
   rm gmail_token.json gmail_token.pickle
   ```

2. Re-run the script for authentication

## Monitoring and Maintenance

### Check Running Status

```bash
# Check process
ps aux | grep heartbeat_monitor

# View logs
tail -f heartbeat_monitor.log

# View recent check records
grep "Website running" heartbeat_monitor.log | tail -20
```

### Stop Monitoring

```bash
# Find process ID
ps aux | grep heartbeat_monitor

# Stop process
kill <process_id>

# Or use systemd
sudo systemctl stop heartbeat-monitor
```

### Update Configuration

After editing `heartbeat_config.json`, restart monitoring:

```bash
# If using nohup
kill <process_id>
nohup python3 heartbeat_monitor.py > heartbeat.log 2>&1 &

# If using systemd
sudo systemctl restart heartbeat-monitor
```

## Security Recommendations

1. **Protect sensitive files**:
   ```bash
   chmod 600 gmail_credentials.json
   chmod 600 gmail_token.json
   chmod 600 heartbeat_config.json
   ```

2. **Do not commit to Git**:
   Add to `.gitignore`:
   ```
   gmail_credentials.json
   gmail_token.json
   gmail_token.pickle
   heartbeat_config.json
   heartbeat_monitor.log
   ```

3. **Use dedicated account**: It is recommended to use a dedicated Gmail account for monitoring, rather than a personal account

