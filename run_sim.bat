@echo off
setlocal enabledelayedexpansion

:: Configuration
set SIMULATION_DURATION=60
set SQS_INIT_DELAY=2

:: Start SQS utility
echo Starting SQS utility...
start /b python sqsUtility.py
set SQS_PID=!ERRORLEVEL!

:: Give SQS utility a moment to initialize
timeout /t %SQS_INIT_DELAY% >nul

:: Start Simulation Core
echo Starting Simulation Core...
start /b python simCore.py
set CORE_PID=!ERRORLEVEL!

:: Start Agent Module
echo Starting Agent Module...
start /b python agentModule.py
set AGENT_PID=!ERRORLEVEL!

:: Start Traffic Control System
echo Starting Traffic Control System...
start /b python trafficModule.py
set TRAFFIC_PID=!ERRORLEVEL!

:: Start Visualization Module
echo Starting Visualization Module...
start /b python visualizationModule.py
set VIZ_PID=!ERRORLEVEL!

echo All components started. Simulation running...
echo Visualization dashboard available at http://localhost:8050
echo Press Ctrl+C to stop the simulation and close all components.

:: Wait for the specified duration
timeout /t %SIMULATION_DURATION% >nul

:LOOP
tasklist | find " %VIZ_PID% " >nul
if not errorlevel 1 (
    timeout /t 1 >nul
    goto :LOOP
)

:: Terminate all processes
:TERMINATE
echo Terminating all components...
taskkill /PID %SQS_PID% /F >nul 2>&1
taskkill /PID %CORE_PID% /F >nul 2>&1
taskkill /PID %AGENT_PID% /F >nul 2>&1
taskkill /PID %TRAFFIC_PID% /F >nul 2>&1
taskkill /PID %VIZ_PID% /F >nul 2>&1

echo Simulation and visualization terminated.
exit /b
