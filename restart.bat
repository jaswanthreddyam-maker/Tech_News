@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev_toolkit\restart.ps1" %*
