@echo off
rem DM-souba: fetch latest prices locally, then commit and push.
rem Double-click this file to update the site data.

cd /d "%~dp0"

echo === [1/4] Fetching prices from Yuyutei (takes 15-40 min) ===
python fetch_yuyutei.py --all --delay 1.0
if errorlevel 1 (
    echo.
    echo FETCH FAILED. Nothing was pushed.
    pause
    exit /b 1
)

echo === [2/4] Validating data ===
python scripts\validate_cards.py
if errorlevel 1 (
    echo.
    echo VALIDATION FAILED. Nothing was pushed.
    pause
    exit /b 1
)

echo === [3/4] Committing ===
git add public/cards.json public/meta.json cards.json meta.json
git diff --staged --quiet && echo No price changes. && goto :done

git commit -m "chore: update card prices (local)"
if errorlevel 1 (
    echo COMMIT FAILED.
    pause
    exit /b 1
)

echo === [4/4] Pushing (Cloudflare will redeploy automatically) ===
git push origin main
if errorlevel 1 (
    echo PUSH FAILED. Run "git push origin main" manually.
    pause
    exit /b 1
)

:done
echo.
echo All done! Site will update in a few minutes.
pause
