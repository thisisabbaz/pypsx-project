@echo off
cd /d E:\psx-dashboard
call .venv\Scripts\activate.bat
python scanner.py >> data\scanner.log 2>&1