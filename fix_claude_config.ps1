i # PowerShell script to fix Claude Desktop MCP configuration
# Run this with: .\fix_claude_config.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Claude Desktop MCP Config Fixer" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Paths
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
$projectPath = "C:\Users\toddb\PycharmProjects\exilePriceCheck"
$pythonPath = "$projectPath\.venv\Scripts\python.exe"
$serverPath = "$projectPath\mcp_poe_server.py"

# Check if Claude config exists
if (Test-Path $configPath) {
    Write-Host "[✓] Found Claude Desktop config at:" -ForegroundColor Green
    Write-Host "    $configPath" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[✗] Claude Desktop config not found!" -ForegroundColor Red
    Write-Host "    Expected at: $configPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please install Claude Desktop first:" -ForegroundColor Yellow
    Write-Host "https://claude.ai/download" -ForegroundColor Blue
    exit 1
}

# Check if Python exists
if (Test-Path $pythonPath) {
    Write-Host "[✓] Found Python virtual environment:" -ForegroundColor Green
    Write-Host "    $pythonPath" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[!] Virtual environment not found, will use system Python" -ForegroundColor Yellow
    $pythonPath = "python"
    Write-Host ""
}

# Check if MCP server exists
if (Test-Path $serverPath) {
    Write-Host "[✓] Found MCP server:" -ForegroundColor Green
    Write-Host "    $serverPath" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[✗] MCP server not found!" -ForegroundColor Red
    Write-Host "    Expected at: $serverPath" -ForegroundColor Gray
    exit 1
}

# Backup existing config
$backupPath = "$configPath.backup"
if (Test-Path $configPath) {
    Copy-Item $configPath $backupPath -Force
    Write-Host "[✓] Created backup at:" -ForegroundColor Green
    Write-Host "    $backupPath" -ForegroundColor Gray
    Write-Host ""
}

# Create new config
$config = @{
    mcpServers = @{
        "PoE Price Checker" = @{
            command = $pythonPath
            args = @($serverPath)
        }
    }
} | ConvertTo-Json -Depth 10

# Write config
$config | Set-Content $configPath -Encoding UTF8

Write-Host "[✓] Updated Claude Desktop configuration!" -ForegroundColor Green
Write-Host ""
Write-Host "New configuration:" -ForegroundColor Cyan
Write-Host $config -ForegroundColor Gray
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "1. Close Claude Desktop completely" -ForegroundColor Yellow
Write-Host "2. Restart Claude Desktop" -ForegroundColor Yellow
Write-Host "3. In Claude, ask: 'What tools do you have available?'" -ForegroundColor Yellow
Write-Host "4. You should see: parse_item, get_item_price, etc." -ForegroundColor Yellow
Write-Host ""
Write-Host "If you have issues, see: CLAUDE_DESKTOP_FIX.md" -ForegroundColor Gray
Write-Host ""
Write-Host "[✓] Done!" -ForegroundColor Green
