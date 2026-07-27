@echo off
rem DM-souba: fetch latest prices locally, then commit and push.
rem Usage:
rem   update_prices.bat              - interactive / Task Scheduler
rem   update_prices.bat scheduled    - same (explicit scheduled mode)
rem Window always closes automatically when finished (no pause).

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\update_prices.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "EXITCODE=0"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=manual"

call :log "========== START mode=%MODE% =========="
call :log "cwd=%CD%"

echo === [1/4] Fetching prices from Yuyutei (takes 15-40 min) ===
call :log "[1/4] fetch start"
python fetch_yuyutei.py --all --delay 1.0 >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "EXITCODE=1"
    echo FETCH FAILED. Nothing was pushed.
    call :log "[1/4] FETCH FAILED"
    goto :finish
)
call :log "[1/4] fetch OK"

echo === [2/4] Validating data ===
call :log "[2/4] validate start"
python scripts\validate_cards.py >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "EXITCODE=1"
    echo VALIDATION FAILED. Nothing was pushed.
    call :log "[2/4] VALIDATION FAILED"
    goto :finish
)
call :log "[2/4] validate OK"

echo === [3/4] Committing ===
call :log "[3/4] commit start"
git add public/cards.json public/meta.json cards.json meta.json >>"%LOG_FILE%" 2>&1
git diff --staged --quiet
if not errorlevel 1 (
    echo No price changes.
    call :log "[3/4] no price changes"
    goto :finish
)

git commit -m "chore: update card prices (local)" >>"%LOG_FILE%" 2>&1
if errorlevel 1 (
    set "EXITCODE=1"
    echo COMMIT FAILED.
    call :log "[3/4] COMMIT FAILED"
    goto :finish
)
call :log "[3/4] commit OK"

echo === [4/4] Pushing (Cloudflare will redeploy automatically) ===
call :log "[4/4] push start"
git push origin main >>"%LOG_FILE%" 2>&1
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
if "!EXITCODE!"=="0" (
    call :log "========== END SUCCESS =========="
) else (
    call :log "========== END FAILED exit=!EXITCODE! =========="
)
echo.
echo Log: %LOG_FILE%
rem Auto-close: no pause. Brief delay only when started by double-click (not scheduled).
if /I not "%MODE%"=="scheduled" timeout /t 3 /nobreak >nul
exit /b !EXITCODE!

:log
>>"%LOG_FILE%" echo [%DATE% %TIME%] %~1
echo [%DATE% %TIME%] %~1
exit /b 0
