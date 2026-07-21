@echo off
cd /d "%~dp0"
rem uvw + pythonw = run without a console window (logs still go to logs\sync.log)
start "" uvw run pythonw main.py
