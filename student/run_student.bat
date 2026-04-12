@echo off
title Classroom Student Agent (Admin Mode)
echo ========================================
echo Classroom Student Agent - Administrator Mode
echo ========================================
echo.
echo This will run the student agent with FULL
echo internet blocking capabilities.
echo.
echo Requesting administrator privileges...
echo.

:: Create VBS script to run as admin
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
echo UAC.ShellExecute "cmd", "/c cd /d %~dp0 && python main.py", "", "runas", 1 >> "%temp%\getadmin.vbs"

:: Run the VBS script
"%temp%\getadmin.vbs"
del "%temp%\getadmin.vbs"

pause