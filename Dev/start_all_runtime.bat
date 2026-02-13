@echo off
setlocal

cd /d "C:\Users\mglav\Projects\AI Trader\Dev"

echo [1/4] Starting auto-trading...
start "AI Trader - Auto Trading" cmd /k "cd /d C:\Users\mglav\Projects\AI Trader\Dev && python run_auto_trading.py"

echo [2/4] Starting dashboard...
start "AI Trader - Dashboard" cmd /k "cd /d C:\Users\mglav\Projects\AI Trader\Dev && python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false"

echo [3/4] Enabling Tailscale Serve/Funnel for port 8501...
tailscale serve reset
tailscale serve --bg 8501
tailscale funnel --bg 8501

echo [4/4] Current funnel status:
tailscale funnel status

echo.
echo Runtime startup sequence completed.
echo If public URL is not reachable, rerun this script.

endlocal
