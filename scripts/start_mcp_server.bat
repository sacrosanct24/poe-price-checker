@echo off
REM Quick launcher for PoE Price Checker MCP Server
REM No Node.js required - uses Python directly

echo ================================================
echo    PoE Price Checker - MCP Server
echo ================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the MCP server
python mcp_poe_server.py

pause
