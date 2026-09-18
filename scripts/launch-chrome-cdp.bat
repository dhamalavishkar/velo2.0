@echo off
echo Starting Chrome with CDP on port 9222...
set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
set USER_DATA_DIR="C:\ChromeDevProfile"
if not exist %USER_DATA_DIR% mkdir %USER_DATA_DIR%
%CHROME_PATH% --remote-debugging-port=9222 --user-data-dir=%USER_DATA_DIR%