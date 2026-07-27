@echo off
rem DM-souba: fetch latest prices locally, then commit and push.
rem Usage:
rem   update_prices.bat              - interactive / Task Scheduler
rem   update_prices.bat scheduled    - same (explicit scheduled mode)
rem Window always closes automatically when finished (no pause).
rem NOTE: Keep this file ASCII-only (no Japanese) to avoid cmd encoding issues.

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\update_prices.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "EXITCODE=0"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=manual"
set "LOCK_FILE=%LOG_DIR%\update_prices.lock"

if exist "%LOCK_FILE%" (
    powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter 'name=''python.exe''' -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*fetch_yuyutei*' }) { exit 1 } else { exit 0 }"
    if errorlevel 1 goto :locked
    echo Stale lock found. No fetch process running - continuing.
    del "%LOCK_FILE%" >nul 2>&1
)
echo %DATE% %TIME% mode=%MODE% > "%LOCK_FILE%"
goto :main

:locked
echo.
echo Another price update is already running.
echo Wait for it to finish, or end fetch_yuyutei.py in Task Manager.
echo Lock: %LOCK_FILE%
echo.
echo To force unlock, delete the lock file above and run again.
if /I not "%MODE%"=="scheduled" timeout /t 15 /nobreak >nul
exit /b 1

:main
call :log "========== START mode=%MODE% =========="
call :log "cwd=%CD%"

echo.
echo === [1/4] Fetching prices from Yuyutei ===
echo This step takes about 15-40 minutes. Progress appears below.
echo Log file: %LOG_FILE%
echo.
call :log "[1/4] fetch start"
set PYTHONUNBUFFERED=1
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Continue';" ^
  "python -u fetch_yuyutei.py --all --delay 1.0 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append;" ^
  "exit $LASTEXITCODE"
if errorlevel 1 (
    set "EXITCODE=1"
    echo.
    echo FETCH FAILED. Nothing was pushed.
    call :log "[1/4] FETCH FAILED"
    goto :finish
)
call :log "[1/4] fetch OK"

echo.
echo === [2/4] Validating data ===
call :log "[2/4] validate start"
call :tee python -u scripts\validate_cards.py
if errorlevel 1 (
    set "EXITCODE=1"
    echo.
    echo VALIDATION FAILED. Nothing was pushed.
    call :log "[2/4] VALIDATION FAILED"
    goto :finish
)
call :log "[2/4] validate OK"

echo.
echo === [3/4] Committing ===
call :log "[3/4] commit start"
call :tee git add public/cards.json public/meta.json cards.json meta.json
git diff --staged --quiet
if not errorlevel 1 (
    echo No price changes.
    call :log "[3/4] no price changes"
    goto :finish
)

powershell -NoProfile -Command ^
  "$ErrorActionPreference='Continue';" ^
  "git commit -m 'chore: update card prices (local)' 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append;" ^
  "exit $LASTEXITCODE"
if errorlevel 1 (
    set "EXITCODE=1"
    echo COMMIT FAILED.
    call :log "[3/4] COMMIT FAILED"
    goto :finish
)
call :log "[3/4] commit OK"

echo.
echo === [4/4] Pushing (Cloudflare will redeploy automatically) ===
call :log "[4/4] push start"
call :tee git push origin main
if errorlevel 1 (
    set "EXITCODE=1"
    echo PUSH FAILED. Run "git push origin main" manually.
    call :log "[4/4] PUSH FAILED"
    goto :finish
)
call :log "[4/4] push OK"

echo.
echo All done! Site will update in a few minutes.

:finish
if exist "%LOCK_FILE%" del "%LOCK_FILE%" >nul 2>&1
if "!EXITCODE!"=="0" (
    call :log "========== END SUCCESS =========="
) else (
    call :log "========== END FAILED exit=!EXITCODE! =========="
)
echo.
echo Log: %LOG_FILE%
rem Auto-close: no pause. Brief delay only when started by double-click (not scheduled).
if /I not "%MODE%"=="scheduled" timeout /t 8 /nobreak >nul
exit /b !EXITCODE!

:tee
>>"%LOG_FILE%" echo --- %*
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Continue';" ^
  "& %* 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append;" ^
  "exit $LASTEXITCODE"
exit /b %ERRORLEVEL%

:log
>>"%LOG_FILE%" echo [%DATE% %TIME%] %~1
echo [%DATE% %TIME%] %~1
exit /b 0
