@echo off
rem Remove stale lock so update_prices.bat can run again.
cd /d "%~dp0"
set "LOCK=%~dp0logs\update_prices.lock"
if not exist "%LOCK%" (
    echo No lock file. You can run update_prices.bat now.
    goto :done
)
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter 'name=''python.exe''' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*fetch_yuyutei*' }) { Write-Host 'fetch_yuyutei.py is still running. Stop it in Task Manager first.'; exit 1 } else { exit 0 }"
if errorlevel 1 goto :done
del "%LOCK%"
echo Lock removed: %LOCK%
echo You can run update_prices.bat now.
:done
timeout /t 5 /nobreak >nul
