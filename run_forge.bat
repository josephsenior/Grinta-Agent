@echo off
REM Enforce strict CSP for non-Docker local runs
set CSP_POLICY=strict

cd /d "C:\Users\GIGABYTE\Desktop\Forge"
python -c "from forge.cli.entry import main; main()" serve
pause
