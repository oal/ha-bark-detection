#!/bin/bash
#
# Installation script for bark-detector systemd user service
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print with color
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root. This is a USER service."
    exit 1
fi

print_info "Installing bark-detector systemd user service..."
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/bark-detector.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    print_error "Service file not found: $SERVICE_FILE"
    exit 1
fi

# Create systemd user directory if it doesn't exist
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
print_info "Creating systemd user directory: $USER_SYSTEMD_DIR"
mkdir -p "$USER_SYSTEMD_DIR"

# Update service file with actual project path
print_info "Updating service file with project path: $PROJECT_DIR"
sed "s|%h/Projects/ha-bark-detection|$PROJECT_DIR|g" "$SERVICE_FILE" > "$USER_SYSTEMD_DIR/bark-detector.service"

# Verify .env file exists
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found at $ENV_FILE"
    print_warning "Please copy .env.example to .env and configure before starting the service"
    echo
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check for PortAudio system dependency
print_info "Checking for PortAudio system library..."
cd "$PROJECT_DIR"

# Try to import sounddevice to check if PortAudio is available
if ! uv run python -c "import sounddevice" 2>/dev/null; then
    print_error "PortAudio library not found!"
    echo
    print_warning "The sounddevice Python package requires PortAudio at the system level."
    print_warning "Please install it for your distribution:"
    echo
    echo "  Ubuntu/Debian:  sudo apt-get install portaudio19-dev python3-dev"
    echo "  Fedora/RHEL:    sudo dnf install portaudio-devel python3-devel"
    echo "  Arch Linux:     sudo pacman -S portaudio"
    echo
    print_warning "After installing, run this script again."
    exit 1
fi
print_info "✓ PortAudio is available"
echo

# Reload systemd daemon
print_info "Reloading systemd user daemon..."
systemctl --user daemon-reload

# Enable the service
print_info "Enabling bark-detector service..."
systemctl --user enable bark-detector.service

# Offer to start the service
echo
read -p "$(echo -e "${GREEN}?${NC} Do you want to start the service now? [Y/n]: ")" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    print_info "Starting bark-detector service..."
    systemctl --user start bark-detector.service

    # Wait a moment for service to start
    sleep 2

    # Check status
    if systemctl --user is-active --quiet bark-detector.service; then
        print_info "✓ Service is running!"
    else
        print_warning "Service failed to start. Check logs with:"
        echo "  journalctl --user -u bark-detector -f"
        exit 1
    fi
fi

# Enable lingering (allow services to run even when logged out)
print_info "Enabling lingering (allows service to run when logged out)..."
loginctl enable-linger "$USER"

# Print success message
echo
print_info "========================================="
print_info "✓ Installation complete!"
print_info "========================================="
echo
print_info "Useful commands:"
echo "  Start service:   systemctl --user start bark-detector"
echo "  Stop service:    systemctl --user stop bark-detector"
echo "  Restart service: systemctl --user restart bark-detector"
echo "  View status:     systemctl --user status bark-detector"
echo "  View logs:       journalctl --user -u bark-detector -f"
echo "  Disable service: systemctl --user disable bark-detector"
echo
print_info "The service will now start automatically on login."
print_info "Lingering is enabled, so it will run even when logged out."
echo
