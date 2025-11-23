#!/bin/bash
# Server environment one-click configuration script
# Used to automatically install and configure website monitoring system on server

set -e  # Exit immediately if a command exits with a non-zero status

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Main function
main() {
    echo "============================================================"
    echo "  Website Monitoring System - Server Environment Setup"
    echo "============================================================"
    echo ""
    
    # 1. Check Python
    print_info "Checking Python environment..."
    if check_command python3; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Found Python3: $PYTHON_VERSION"
    elif check_command python; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        print_success "Found Python: $PYTHON_VERSION"
    else
        print_error "Python not found, please install Python 3.7 or higher"
        exit 1
    fi
    
    # Check Python version
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
        print_error "Python version too low, requires Python 3.7 or higher (current: $PYTHON_VERSION)"
        exit 1
    fi
    
    echo ""
    
    # 2. Check pip
    print_info "Checking pip..."
    if check_command pip3; then
        PIP_CMD="pip3"
        print_success "Found pip3"
    elif check_command pip; then
        PIP_CMD="pip"
        print_success "Found pip"
    else
        print_warning "pip not found, attempting to install..."
        if [ "$PYTHON_CMD" = "python3" ]; then
            $PYTHON_CMD -m ensurepip --upgrade || {
                print_error "Cannot install pip, please install manually"
                exit 1
            }
            PIP_CMD="pip3"
        else
            $PYTHON_CMD -m ensurepip --upgrade || {
                print_error "Cannot install pip, please install manually"
                exit 1
            }
            PIP_CMD="pip"
        fi
    fi
    
    echo ""
    
    # 3. Check requirements file
    print_info "Checking dependency file..."
    if [ ! -f "requirements_heartbeat.txt" ]; then
        print_error "requirements_heartbeat.txt file not found"
        print_info "Please make sure to run this script in the project directory"
        exit 1
    fi
    print_success "Found dependency file"
    
    echo ""
    
    # 4. Install dependencies
    print_info "Installing Python dependencies..."
    print_info "This may take a few minutes, please wait..."
    echo ""
    
    if $PIP_CMD install -r requirements_heartbeat.txt; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        print_warning "Trying to install with --user option..."
        if $PIP_CMD install --user -r requirements_heartbeat.txt; then
            print_success "Dependencies installed successfully (user directory)"
        else
            print_error "Failed to install dependencies, please check network connection or install manually"
            exit 1
        fi
    fi
    
    echo ""
    
    # 5. Check required files
    print_info "Checking required files..."
    MISSING_FILES=()
    
    if [ ! -f "heartbeat_monitor.py" ]; then
        MISSING_FILES+=("heartbeat_monitor.py")
    fi
    
    if [ ! -f "heartbeat_config.json" ]; then
        MISSING_FILES+=("heartbeat_config.json")
        print_warning "heartbeat_config.json not found, will create default config"
    fi
    
    if [ ! -f "gmail_credentials.json" ]; then
        MISSING_FILES+=("gmail_credentials.json")
        print_warning "gmail_credentials.json not found (need to download from Google Cloud)"
    fi
    
    if [ ${#MISSING_FILES[@]} -eq 0 ]; then
        print_success "All required files exist"
    else
        print_warning "Missing the following files: ${MISSING_FILES[*]}"
    fi
    
    echo ""
    
    # 6. Check configuration file
    if [ -f "heartbeat_config.json" ]; then
        print_info "Checking configuration file..."
        if grep -q "your-email@example.com" heartbeat_config.json 2>/dev/null; then
            print_warning "Configuration file contains default values, please edit heartbeat_config.json to set correct email addresses"
        else
            print_success "Configuration file appears to be configured"
        fi
    else
        print_warning "Creating default configuration file..."
        cat > heartbeat_config.json << 'EOF'
{
  "recipient_email": ["your-email@example.com"],
  "sender_email": "your-email@gmail.com",
  "check_interval": 1800,
  "timeout": 30,
  "max_consecutive_failures": 3
}
EOF
        print_success "Created default configuration file heartbeat_config.json"
        print_warning "Please edit this file to set correct email addresses"
    fi
    
    echo ""
    
    # 7. Set execution permissions
    print_info "Setting script execution permissions..."
    if [ -f "heartbeat_monitor.py" ]; then
        chmod +x heartbeat_monitor.py
        print_success "Set execution permission for heartbeat_monitor.py"
    fi
    
    if [ -f "test_email.py" ]; then
        chmod +x test_email.py
        print_success "Set execution permission for test_email.py"
    fi
    
    echo ""
    
    # 8. Verify installation
    print_info "Verifying installation..."
    if $PYTHON_CMD -c "import requests; import google.auth; import googleapiclient" 2>/dev/null; then
        print_success "Core dependencies verified successfully"
    else
        print_warning "Some dependencies may not be installed correctly, but you can try to run anyway"
    fi
    
    echo ""
    echo "============================================================"
    print_success "Environment setup completed!"
    echo "============================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Make sure the following files are ready:"
    echo "   - gmail_credentials.json (download from Google Cloud Console)"
    echo "   - heartbeat_config.json (created, please edit to set email addresses)"
    echo ""
    echo "2. First run requires authentication (run once on local MacBook to get token):"
    echo "   $PYTHON_CMD test_email.py"
    echo "   Then copy gmail_token.json and gmail_token.pickle to server"
    echo ""
    echo "3. Or run directly on server (will prompt for OAuth authentication):"
    echo "   $PYTHON_CMD heartbeat_monitor.py"
    echo ""
    echo "4. Run monitoring in background:"
    echo "   nohup $PYTHON_CMD heartbeat_monitor.py > heartbeat.log 2>&1 &"
    echo ""
    echo "5. View logs:"
    echo "   tail -f heartbeat_monitor.log"
    echo ""
    echo "============================================================"
}

# Run main function
main
