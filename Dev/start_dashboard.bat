@echo off
cd /d "C:\Users\mglav\Projects\AI Trader\Dev"
python -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501
