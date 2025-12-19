#!/usr/bin/env bash
# Environment Snapshot Collection Script
# Captures current environment state for modernization baseline
# Usage: ./ops/inventory/collect_env_snapshot.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INVENTORY_DIR="${REPO_ROOT}/docs/modernization/inventory"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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

# Ensure we're in the correct directory
if [[ ! -f "${REPO_ROOT}/main.py" ]]; then
    error "This script must be run from the poe-price-checker repository"
fi

# Create inventory directory
log "Creating inventory directory: ${INVENTORY_DIR}"
mkdir -p "${INVENTORY_DIR}"

# Function to capture and save output
capture_output() {
    local filename="$1"
    local description="$2"
    local command="$3"
    
    log "Capturing ${description}..."
    echo "=== ${description} ===" > "${INVENTORY_DIR}/${filename}"
    echo "Captured: ${TIMESTAMP}" >> "${INVENTORY_DIR}/${filename}"
    echo "Command: ${command}" >> "${INVENTORY_DIR}/${filename}"
    echo "" >> "${INVENTORY_DIR}/${filename}"
    
    if eval "${command}" >> "${INVENTORY_DIR}/${filename}" 2>&1; then
        log "✓ ${description} captured successfully"
    else
        warn "⚠ ${description} capture had issues (check output)"
    fi
    
    echo "" >> "${INVENTORY_DIR}/${filename}"
    echo "=== End ${description} ===" >> "${INVENTORY_DIR}/${filename}"
    
    # Also print to stdout
    echo -e "\n${BLUE}=== ${description} ===${NC}"
    eval "${command}" 2>&1 | head -100
    echo -e "${BLUE}=== End ${description} ===${NC}\n"
}

# 1. Python and pip information
capture_output "python_info.txt" "Python and pip information" "python3 --version && pip3 --version"

# 2. Virtual environment information (if activated)
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    capture_output "venv_info.txt" "Virtual Environment Information" "echo \"Virtual Environment: ${VIRTUAL_ENV}\" && python -c 'import sys; print(\"Python executable:\", sys.executable)'"
else
    warn "No virtual environment detected. Consider activating .venv for accurate dependency capture."
    capture_output "venv_info.txt" "Virtual Environment Information" "echo \"No virtual environment activated\" && which python3 && which pip3"
fi

# 3. Development dependencies (from requirements-dev.txt)
if [[ -f "${REPO_ROOT}/requirements-dev.txt" ]]; then
    capture_output "dev_dependencies.txt" "Development Dependencies" "pip3 list --format=freeze"
else
    warn "requirements-dev.txt not found"
fi

# 4. Runtime dependencies (from requirements.txt)
if [[ -f "${REPO_ROOT}/requirements.txt" ]]; then
    capture_output "runtime_dependencies.txt" "Runtime Dependencies" "cd /tmp && python3 -m venv temp_venv && source temp_venv/bin/activate && pip install -r ${REPO_ROOT}/requirements.txt && pip list --format=freeze && deactivate && rm -rf temp_venv"
else
    warn "requirements.txt not found"
fi

# 5. OS Information
capture_output "os_info.txt" "Operating System Information" "uname -a && echo '' && cat /etc/os-release 2>/dev/null || echo 'OS release info not available'"

# 6. Git Information
capture_output "git_info.txt" "Git Repository Information" "git rev-parse --show-toplevel && git rev-parse --short HEAD && git status --porcelain && git branch -a && git remote -v"

# 7. CI/CD Workflow Summary
if [[ -d "${REPO_ROOT}/.github/workflows" ]]; then
    log "Analyzing CI/CD workflows..."
    
    # Create workflow summary
    {
        echo "=== CI/CD Workflow Summary ==="
        echo "Captured: ${TIMESTAMP}"
        echo ""
        echo "Workflows found:"
        ls -1 "${REPO_ROOT}/.github/workflows/" | grep -E '\.(yml|yaml)$'
        echo ""
        
        # Extract Python versions and primary commands from workflows
        echo "Python versions used in workflows:"
        grep -r "python-version" "${REPO_ROOT}/.github/workflows/" | sed 's/.*python-version:[[:space:]]*//;s/[\"'\'']//g'
        echo ""
        
        echo "Primary commands in workflows:"
        grep -r "run:" "${REPO_ROOT}/.github/workflows/" | head -20
        echo ""
        
        echo "=== End CI/CD Workflow Summary ==="
    } > "${INVENTORY_DIR}/ci_cd_summary.txt"
    
    # Also print to stdout
    echo -e "\n${BLUE}=== CI/CD Workflow Summary ===${NC}"
    cat "${INVENTORY_DIR}/ci_cd_summary.txt"
    echo -e "${BLUE}=== End CI/CD Workflow Summary ===${NC}\n"
    
    log "✓ CI/CD workflow analysis completed"
else
    warn ".github/workflows directory not found"
fi

# 8. Project Structure Overview
capture_output "project_structure.txt" "Project Structure Overview" "find . -maxdepth 3 -type d | sort"

# 9. Key Configuration Files
log "Capturing key configuration files..."
for config_file in ".pre-commit-config.yaml" "mypy.ini" ".flake8" "pytest.ini" "pyproject.toml" "setup.py" "tox.ini"; do
    if [[ -f "${REPO_ROOT}/${config_file}" ]]; then
        capture_output "config_${config_file//\//_}.txt" "Configuration: ${config_file}" "cat ${REPO_ROOT}/${config_file}"
    fi
done

# 10. Environment Variables (sanitized)
capture_output "env_vars.txt" "Environment Variables (sanitized)" "env | grep -E '^(PATH|PYTHON|HOME|USER|LANG|LC_|SHELL|TERM)' | sort"

# 11. System Resources
capture_output "system_resources.txt" "System Resources" "echo 'CPU Info:' && nproc && echo '' && echo 'Memory Info:' && free -h && echo '' && echo 'Disk Usage:' && df -h ."

# Create summary report
log "Creating summary report..."
{
    echo "=== Environment Snapshot Summary ==="
    echo "Captured: ${TIMESTAMP}"
    echo "Repository: ${REPO_ROOT}"
    echo "Script: ${BASH_SOURCE[0]}"
    echo ""
    echo "Files generated in: ${INVENTORY_DIR}"
    echo ""
    echo "Generated files:"
    ls -1 "${INVENTORY_DIR}/" | grep -v "^$"
    echo ""
    echo "=== End Summary ==="
} > "${INVENTORY_DIR}/snapshot_summary.txt"

# Print summary to stdout
echo -e "\n${GREEN}=== Environment Snapshot Summary ===${NC}"
cat "${INVENTORY_DIR}/snapshot_summary.txt"
echo -e "${GREEN}=== End Summary ===${NC}\n"

log "Environment snapshot collection completed successfully!"
log "All files saved to: ${INVENTORY_DIR}"

# Verify all expected files were created
log "Verifying generated files..."
expected_files=(
    "python_info.txt"
    "venv_info.txt"
    "dev_dependencies.txt"
    "runtime_dependencies.txt"
    "os_info.txt"
    "git_info.txt"
    "ci_cd_summary.txt"
    "project_structure.txt"
    "env_vars.txt"
    "system_resources.txt"
    "snapshot_summary.txt"
)

missing_files=()
for file in "${expected_files[@]}"; do
    if [[ -f "${INVENTORY_DIR}/${file}" ]]; then
        info "✓ ${file}"
    else
        missing_files+=("${file}")
        warn "✗ ${file} (missing)"
    fi
done

if [[ ${#missing_files[@]} -gt 0 ]]; then
    warn "Some files were not generated. Check the output above for details."
else
    log "All expected files generated successfully!"
fi

# Make the script executable
chmod +x "${SCRIPT_DIR}/collect_env_snapshot.sh"

log "Script completed. Inventory files are ready for review."
