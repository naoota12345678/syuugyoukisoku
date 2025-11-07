@echo off
echo Setting up API key...
if not exist .env copy .env.example .env
notepad .env
pause
