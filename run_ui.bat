@echo off
REM Starts the local HTML interface from this folder.
echo Starting the dashboard accuracy-check page...
python "%~dp0run_ui.py"
REM Keeps the window open if the server stops or reports an error.
pause
