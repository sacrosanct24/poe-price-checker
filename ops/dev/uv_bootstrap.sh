#!/usr/bin/env bash
# UV Bootstrap Script for PoE Price Checker
# This script sets up an optional uv environment for development
# It is idempotent and safe to re-run
# Usage: bash ops/dev/uv_bootstrap.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
PYTHON_VERSION="3.11"

# Ensure we're in the correct directory
if [[ ! -f "${REPO_ROOT}/main.py" ]]; then
    error "This script must be run from the poe-price-checker repository"
fi

# Change to repo root
cd "${REPO_ROOT}"

log "UV Bootstrap Script Starting"
log "Repository: ${REPO_ROOT}"
log "Python version: ${PYTHON_VERSION}"

# Function to check if uv is installed
check_uv_installed() {
    if command -v uv &> /dev/null; then
        log "UV is already installed: $(uv --version)"
        return 0
    else
        warn "UV is not installed"
        return 1
    fi
}

# Function to install uv
install_uv() {
    log "Installing UV..."
    
    # Try to install uv using the official installer
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        log "UV installed successfully via installer"
        
        # Add uv to PATH for this session
        export PATH="$HOME/.local/bin:$PATH"
        
        # Verify installation
        if command -v uv &> /dev/null; then
            log "UV is now available: $(uv --version)"
            return 0
        else
            error "UV installation completed but command not found in PATH"
        fi
    else
        error "Failed to install UV via installer"
    fi
}

# Function to create uv virtual environment
create_venv() {
    log "Creating virtual environment with UV..."
    
    if [[ -d "${VENV_DIR}" ]]; then
        log "Virtual environment already exists at ${VENV_DIR}"
        
        # Check if it's a valid venv
        if [[ -f "${VENV_DIR}/pyvenv.cfg" ]]; then
            log "Existing virtual environment is valid"
            return 0
        else
            warn "Existing virtual environment is invalid, recreating..."
            rm -rf "${VENV_DIR}"
        fi
    fi
    
    # Create new venv
    if uv venv --python "${PYTHON_VERSION}" --no-install-proxies; then
        log "Virtual environment created at ${VENV_DIR}"
        return 0
    else
        error "Failed to create virtual environment"
    fi
}

# Function to activate virtual environment
activate_venv() {
    log "Activating virtual environment..."
    
    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        source "${VENV_DIR}/bin/activate"
        log "Virtual environment activated"
        
        # Verify Python version
        CURRENT_PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        log "Using Python ${CURRENT_PYTHON_VERSION}"
        
        return 0
    else
        error "Virtual environment activation failed - activation script not found"
    fi
}

# Function to install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    # Install runtime dependencies
    if [[ -f "requirements.txt" ]]; then
        log "Installing runtime dependencies from requirements.txt..."
        uv pip install -r requirements.txt
        log "Runtime dependencies installed"
    else
        warn "requirements.txt not found, skipping runtime dependencies"
    fi
    
    # Install dev dependencies
    if [[ -f "requirements-dev.txt" ]]; then
        log "Installing dev dependencies from requirements-dev.txt..."
        uv pip install -r requirements-dev.txt
        log "Dev dependencies installed"
    else
        warn "requirements-dev.txt not found, skipping dev dependencies"
    fi
}

# Function to run checks
run_checks() {
    log "Running checks..."
    
    if [[ -f "check.sh" ]]; then
        log "Running ./check.sh..."
        ./check.sh
        log "Checks completed successfully"
    else
        warn "check.sh not found, skipping checks"
    fi
}

# Function to print summary
print_summary() {
    log "UV Bootstrap Summary"
    echo ""
    echo "Virtual Environment: ${VENV_DIR}"
    echo "Python Version: ${PYTHON_VERSION}"
    echo ""
    echo "To activate the environment manually:"
    echo "  source ${VENV_DIR}/bin/activate"
    echo ""
    echo "To run checks manually:"
    echo "  ./check.sh"
    echo ""
    echo "To deactivate:"
    echo "  deactivate"
    echo ""
}

# Main execution
main() {
    log "Starting UV bootstrap process..."
    
    # Check if uv is installed, install if needed
    if ! check_uv_installed; then
        install_uv
    fi
    
    # Create and activate virtual environment
    create_venv
    activate_venv
    
    # Install dependencies
    install_dependencies
    
    # Run checks
    run_checks
    
    # Print summary
    print_summary
    
    log "UV bootstrap completed successfully!"
}

# Run main function
main "$@"
